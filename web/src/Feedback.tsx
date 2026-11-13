import { useState } from 'react'
import { sendFeedback, type FeedbackResponse } from './api'

export default function Feedback({ question, predSql }: { question: string; predSql: string }) {
  const [open, setOpen] = useState(false)
  const [sql, setSql] = useState(predSql)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [res, setRes] = useState<FeedbackResponse | null>(null)

  async function save() {
    setSaving(true)
    try {
      setRes(await sendFeedback({ question, pred_sql: predSql, sql, note }))
    } catch (err) {
      setRes({ ok: false, error: `요청 실패: ${(err as Error).message}` })
    } finally {
      setSaving(false)
    }
  }

  if (!open) return <button type="button" className="fb-open" onClick={() => setOpen(true)}>틀렸어요</button>
  if (res?.ok)
    return (
      <div className="alert ok">
        {res.id}로 회귀 셋에 저장했어요. 정답 결과: {res.rows?.slice(0, 3).map((r) => r.join(', ')).join(' / ')}
      </div>
    )
  return (
    <div className="feedback">
      <label>올바른 SQL (생성된 SQL을 고쳐 주세요)</label>
      <textarea value={sql} onChange={(e) => setSql(e.target.value)} rows={6} />
      <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="무엇이 틀렸나요? 예: 예정일은 날짜만 있음" />
      {res && !res.ok && <div className="alert">{res.error}</div>}
      <button type="button" onClick={save} disabled={saving || !sql.trim()}>{saving ? '확인 중…' : '정답으로 저장'}</button>
    </div>
  )
}
