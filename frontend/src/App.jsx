import { useEffect, useState } from 'react'
import LandingPage from './pages/LandingPage'
import ToolApp from './pages/ToolApp'

function routeFromHash() {
  return window.location.hash.startsWith('#/app') ? 'app' : 'landing'
}

export default function App() {
  const [route, setRoute] = useState(routeFromHash)

  useEffect(() => {
    const onHashChange = () => {
      setRoute(routeFromHash())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return route === 'app' ? <ToolApp /> : <LandingPage />
}
