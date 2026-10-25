import { useEffect, useState } from 'react'

const BASE = import.meta.env.VITE_API_BASE || ''

export async function getJson(path, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v))
  const url = `${BASE}/api${path}${qs.size ? `?${qs}` : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}

export function useApi(path, params = {}) {
  const key = JSON.stringify([path, params])
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    let live = true
    setState((s) => ({ ...s, loading: true }))
    getJson(path, params)
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((error) => live && setState({ data: null, error, loading: false }))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}
