import { useEffect, useState, type FormEvent } from 'react'
import { ask, getExamples, getHealth, type AskResponse, type Health } from './api'

const fmt = (v: unknown) =>
  typeof v === 'number' ? v.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) : v == null ? '—' : String(v)

export default function App() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AskResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [netError, setNetError] = useState<string | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [examples, setExamples] = useState<string[]>([])

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setNetError('API 서버에 연결할 수 없어요. uvicorn이 켜져 있는지 확인해주세요.'))
    getExamples().then(setExamples).catch(() => {})
  }, [])

  async function submit(e?: FormEvent, q = question) {
    e?.preventDefault()
    if (!q.trim() || loading) return
    setQuestion(q)
    setLoading(true)
    setNetError(null)
    try {
      setResult(await ask(q))
    } catch (err) {
      setNetError(`요청 실패: ${(err as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="wrap">
      <header>
        <h1>Olist 데이터에 물어보기</h1>
        <p className="sub">
          자연어 질문 → LLM이 SQL 작성 → 안전검사 → 읽기 전용 실행
          {health && (
            <span className={`badge ${health.mock ? 'mock' : ''}`}>
              {health.mock ? 'MOCK' : health.model} · {health.version}
            </span>
          )}
        </p>
      </header>

      <form onSubmit={submit} className="ask">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="예: 2017년에 들어온 주문은 몇 건이야?"
          maxLength={500}
          autoFocus
        />
        <button disabled={loading || !question.trim()}>{loading ? '꺼내는 중…' : '꺼내줘'}</button>
      </form>

      {examples.length > 0 && (
        <div className="chips">
          {examples.map((ex) => (
            <button key={ex} type="button" onClick={() => submit(undefined, ex)} disabled={loading}>
              {ex}
            </button>
          ))}
        </div>
      )}

      {netError && <div className="alert">{netError}</div>}

      {result && (
        <section className="result">
          {result.interpretation && <div className="interp">해석: {result.interpretation}</div>}
          {result.sql && (
            <details open>
              <summary>생성된 SQL</summary>
              <pre>{result.sql}</pre>
            </details>
          )}

          {result.error ? (
            <div className={`alert ${result.error_type}`}>{result.error}</div>
          ) : result.rows.length === 0 ? (
            <div className="empty">결과가 없어요 (0행)</div>
          ) : (
            <>
              <div className="meta">{result.rows.length.toLocaleString()}행{result.rows.length >= 1000 && ' (최대 1000행으로 제한)'}</div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((v, j) => (
                          <td key={j} className={typeof v === 'number' ? 'num' : ''}>{fmt(v)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </main>
  )
}
