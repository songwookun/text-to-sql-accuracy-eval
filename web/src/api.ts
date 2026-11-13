export type AskResponse = {
  question: string
  sql: string
  interpretation: string
  undefined_terms: string[]
  warnings: string[]
  columns: string[]
  rows: unknown[][]
  error: string | null
  error_type: 'quota' | 'llm' | 'unsafe' | 'timeout' | 'sql' | null
  model: string
  version: string
  mock: boolean
}

export type Health = { ok: boolean; model: string; version: string; mock: boolean }

export async function ask(question: string): Promise<AskResponse> {
  const r = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getHealth(): Promise<Health> {
  const r = await fetch('/api/health')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function getExamples(): Promise<string[]> {
  const r = await fetch('/api/examples')
  return r.ok ? r.json() : []
}
