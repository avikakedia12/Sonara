#!/usr/bin/env python3
"""Score a transcription against MusicNet ground truth using an
accessibility-weighted error taxonomy, instead of standard precision/recall.

The point: a single wrong key signature or a systematic octave error makes a
piece functionally unusable for a blind musician, while eight enharmonic
spelling quirks barely register -- but F-measure weighs those the same. This
scorer doesn't.

Tiers:
  1 Catastrophic (16): wrong key signature, systematic octave errors
                        (an octave slip affecting a large share of notes)
  2 Severe        (8): isolated octave errors, clustered runs (>=3) of
                        missing/extra notes, tempo off by more than 15 BPM
  3 Moderate       (2): an isolated missing or extra note
  4 Minor          (1): tempo off by a little (<=15 BPM but noticeably)

  W = 16*catastrophic + 8*severe + 2*moderate + 1*minor

Enharmonic spelling (also Tier 4 in the taxonomy) isn't scored here: MIDI
pitch numbers don't carry spelling information (F# and Gb are both 66), so
it can't be measured from note-event comparison alone -- would need to diff
engraved notation, not raw pitches. Reported as N/A rather than faked.

Standard mir_eval onset+pitch F-measure is also printed alongside W, to show
concretely how two transcriptions with a similar F-measure can have very
different real-world usability for a blind musician.
"""
import argparse
import csv
from pathlib import Path

import mir_eval
import numpy as np
from music21 import key, note as m21note, pitch as m21pitch, stream


def load_ground_truth_notes(csv_path: Path, max_seconds: float | None) -> list[dict]:
    notes = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            start = float(row["start_time"]) / 44100.0
            end = float(row["end_time"]) / 44100.0
            if max_seconds is not None and start > max_seconds:
                continue
            notes.append({"start": start, "end": end, "pitch": int(row["note"])})
    return sorted(notes, key=lambda n: n["start"])


def get_estimate_notes(audio_path: Path) -> list[dict]:
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH

    _, midi_data, _ = predict(str(audio_path), model_or_model_path=ICASSP_2022_MODEL_PATH)
    notes = []
    for instrument in midi_data.instruments:
        for n in instrument.notes:
            notes.append({"start": n.start, "end": n.end, "pitch": n.pitch})
    return sorted(notes, key=lambda n: n["start"])


def match_notes(ref: list[dict], est: list[dict], onset_tolerance: float = 0.1):
    """Greedy matching: exact pitch matches first, then octave-only matches
    (same pitch class, different octave) among what's left. Returns
    (exact_matches, octave_matches, missing_ref, extra_est)."""
    ref_used = [False] * len(ref)
    est_used = [False] * len(est)
    exact_matches = []

    for pass_octave in (False, True):
        for i, r in enumerate(ref):
            if ref_used[i]:
                continue
            best_j, best_dt = None, onset_tolerance
            for j, e in enumerate(est):
                if est_used[j]:
                    continue
                same_pitch = e["pitch"] == r["pitch"]
                same_class = (e["pitch"] % 12) == (r["pitch"] % 12) and e["pitch"] != r["pitch"]
                if (not pass_octave and not same_pitch) or (pass_octave and not same_class):
                    continue
                dt = abs(e["start"] - r["start"])
                if dt <= best_dt:
                    best_j, best_dt = j, dt
            if best_j is not None:
                ref_used[i] = True
                est_used[best_j] = True
                exact_matches.append((i, best_j, pass_octave))

    octave_matches = [(i, j) for i, j, is_oct in exact_matches if is_oct]
    pitch_matches = [(i, j) for i, j, is_oct in exact_matches if not is_oct]
    missing_ref = [ref[i] for i in range(len(ref)) if not ref_used[i]]
    extra_est = [est[j] for j in range(len(est)) if not est_used[j]]
    return pitch_matches, octave_matches, missing_ref, extra_est


def cluster_by_time(items: list[dict], gap: float = 0.5) -> list[list[dict]]:
    if not items:
        return []
    items = sorted(items, key=lambda n: n["start"])
    clusters = [[items[0]]]
    for n in items[1:]:
        if n["start"] - clusters[-1][-1]["start"] <= gap:
            clusters[-1].append(n)
        else:
            clusters.append([n])
    return clusters


def estimate_key(notes: list[dict]) -> key.Key:
    s = stream.Stream()
    for n in notes:
        s.append(m21note.Note(m21pitch.Pitch(midi=n["pitch"])))
    return s.analyze("key")


def implied_tempo_bpm(csv_path: Path, max_seconds: float | None) -> float | None:
    """Ground truth has no single tempo field; infer BPM from the slope of
    start_beat vs. start_time (seconds) across the labeled notes."""
    times, beats = [], []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = float(row["start_time"]) / 44100.0
            if max_seconds is not None and t > max_seconds:
                continue
            times.append(t)
            beats.append(float(row["start_beat"]))
    if len(times) < 2:
        return None
    slope, _ = np.polyfit(times, beats, 1)  # beats per second
    return slope * 60.0


def standard_f_measure(ref: list[dict], est: list[dict]) -> dict:
    def to_mir_eval(notes):
        intervals = np.array([[n["start"], max(n["end"], n["start"] + 0.01)] for n in notes])
        pitches_hz = np.array([440.0 * 2 ** ((n["pitch"] - 69) / 12.0) for n in notes])
        return intervals, pitches_hz

    ref_i, ref_p = to_mir_eval(ref)
    est_i, est_p = to_mir_eval(est)
    scores = mir_eval.transcription.precision_recall_f1_overlap(
        ref_i, ref_p, est_i, est_p, offset_ratio=None
    )
    return {"precision": scores[0], "recall": scores[1], "f_measure": scores[2]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth-csv", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=30.0)
    parser.add_argument("--detected-bpm", type=float, default=None, help="Reuse a previously detected tempo instead of re-running beat tracking")
    args = parser.parse_args()

    ref = load_ground_truth_notes(args.ground_truth_csv, args.max_seconds)
    est = get_estimate_notes(args.audio)
    print(f"Ground truth notes: {len(ref)}, estimated notes: {len(est)}")

    pitch_matches, octave_matches, missing, extra = match_notes(ref, est)
    print(f"Exact pitch matches: {len(pitch_matches)}, octave-only matches: {len(octave_matches)}")
    print(f"Missing (in ground truth, not transcribed): {len(missing)}")
    print(f"Extra (transcribed, not in ground truth): {len(extra)}")

    catastrophic = severe = moderate = minor = 0
    notes_log = []

    # --- Tier 1: key signature + systematic octave errors ---
    total_pitch_level_matches = len(pitch_matches) + len(octave_matches)
    octave_fraction = len(octave_matches) / total_pitch_level_matches if total_pitch_level_matches else 0.0
    systematic_octave = octave_fraction >= 0.25 and len(octave_matches) >= 5
    if systematic_octave:
        catastrophic += 1
        notes_log.append(f"[Tier 1] Systematic octave errors: {octave_fraction:.0%} of matches are octave-shifted")

    ref_key = estimate_key([ref[i] for i, _ in pitch_matches] or ref)
    est_key = estimate_key([est[j] for _, j in pitch_matches] or est)
    key_mismatch = (ref_key.tonic.name, ref_key.mode) != (est_key.tonic.name, est_key.mode)
    if key_mismatch:
        catastrophic += 1
        notes_log.append(f"[Tier 1] Key mismatch: ground truth {ref_key} vs. estimate {est_key}")

    # --- Tier 2: isolated octave errors (if not systematic), note-run clusters, tempo way off ---
    if not systematic_octave:
        severe += len(octave_matches)
        if octave_matches:
            notes_log.append(f"[Tier 2] {len(octave_matches)} isolated octave error(s)")

    missing_clusters = cluster_by_time(missing)
    extra_clusters = cluster_by_time(extra)
    for label, clusters in (("missing", missing_clusters), ("extra", extra_clusters)):
        for c in clusters:
            if len(c) >= 3:
                severe += 1
                notes_log.append(f"[Tier 2] Cluster of {len(c)} consecutive {label} notes near t={c[0]['start']:.2f}s")
            else:
                moderate += len(c)

    true_bpm = implied_tempo_bpm(args.ground_truth_csv, args.max_seconds)
    if args.detected_bpm is not None and true_bpm is not None:
        bpm_diff = abs(args.detected_bpm - true_bpm)
        if bpm_diff > 15:
            severe += 1
            notes_log.append(f"[Tier 2] Tempo way off: detected {args.detected_bpm:.1f} BPM vs. implied {true_bpm:.1f} BPM")
        elif bpm_diff > 3:
            minor += 1
            notes_log.append(f"[Tier 4] Tempo slightly off: detected {args.detected_bpm:.1f} BPM vs. implied {true_bpm:.1f} BPM")

    if moderate:
        notes_log.append(f"[Tier 3] {moderate} isolated missing/extra note(s)")

    W = 16 * catastrophic + 8 * severe + 2 * moderate + 1 * minor

    print()
    for line in notes_log:
        print(line)
    print()
    print(f"Tier 1 (catastrophic): {catastrophic}")
    print(f"Tier 2 (severe):       {severe}")
    print(f"Tier 3 (moderate):     {moderate}")
    print(f"Tier 4 (minor):        {minor}")
    print(f"Tier 4 (enharmonic spelling): N/A -- not measurable from MIDI pitch numbers alone")
    print(f"\nWeighted score W = {W}")

    f_scores = standard_f_measure(ref, est)
    print(
        f"\nFor comparison, standard mir_eval note transcription metrics: "
        f"P={f_scores['precision']:.3f} R={f_scores['recall']:.3f} F={f_scores['f_measure']:.3f}"
    )


if __name__ == "__main__":
    main()
