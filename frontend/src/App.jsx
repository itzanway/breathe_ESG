import { useState, useEffect, useCallback } from 'react'
import { fetchSummary, fetchRecords, fetchBatches, approveRecord, rejectRecord, uploadFile } from './api'
import './App.css'

const SCOPE_COLORS = { 1: '#e74c3c', 2: '#3498db', 3: '#f39c12' }
const STATUS_COLORS = {
  pending: '#95a5a6', approved: '#27ae60',
  rejected: '#e74c3c', suspicious: '#e67e22'
}
const SOURCE_LABELS = { sap: 'SAP Fuel & Procurement', utility: 'Utility Electricity', travel: 'Corporate Travel' }

function Badge({ label, color }) {
  return (
    <span style={{
      background: color + '22', color, border: `1px solid ${color}55`,
      borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600,
      textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'nowrap'
    }}>{label}</span>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 8, padding: '16px 20px',
      border: '1px solid #e8e8e8', minWidth: 120, flex: 1
    }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || '#111' }}>{value}</div>
      <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function UploadPanel({ onUploaded }) {
  const [uploading, setUploading] = useState({})
  const [results, setResults] = useState({})

  const handleUpload = async (source, e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(u => ({ ...u, [source]: true }))
    try {
      const res = await uploadFile(source, file)
      setResults(r => ({ ...r, [source]: res }))
      onUploaded()
    } catch (err) {
      setResults(r => ({ ...r, [source]: { error: 'Upload failed' } }))
    }
    setUploading(u => ({ ...u, [source]: false }))
    e.target.value = ''
  }

  const sources = [
    { key: 'sap', label: 'SAP Fuel & Procurement', hint: 'CSV with columns: doc_date, quantity, unit, material, plant, vendor', accept: '.csv' },
    { key: 'utility', label: 'Utility Electricity', hint: 'CSV with columns: billing_period_start, consumption_kwh, meter_id, site', accept: '.csv' },
    { key: 'travel', label: 'Corporate Travel', hint: 'JSON array with type, date, origin, destination (flights) or nights/city (hotel)', accept: '.json,.csv' },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
      {sources.map(({ key, label, hint, accept }) => (
        <div key={key} style={{
          background: '#fff', borderRadius: 8, border: '1px solid #e8e8e8',
          padding: 20, display: 'flex', flexDirection: 'column', gap: 10
        }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{label}</div>
          <div style={{ fontSize: 11, color: '#888', lineHeight: 1.5 }}>{hint}</div>
          <label style={{
            display: 'block', background: '#f5f7ff', border: '1px dashed #aac',
            borderRadius: 6, padding: '10px 12px', cursor: 'pointer',
            fontSize: 12, color: '#556', textAlign: 'center'
          }}>
            {uploading[key] ? '⏳ Uploading...' : '↑ Choose file to upload'}
            <input type="file" accept={accept} style={{ display: 'none' }}
              onChange={e => handleUpload(key, e)} disabled={uploading[key]} />
          </label>
          {results[key] && (
            <div style={{
              fontSize: 11, padding: '6px 10px', borderRadius: 4,
              background: results[key].error ? '#fff0f0' : '#f0fff4',
              color: results[key].error ? '#c0392b' : '#27ae60'
            }}>
              {results[key].error
                ? `Error: ${results[key].error}`
                : `✓ ${results[key].rows_created} rows ingested, ${results[key].rows_failed} failed`}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function RecordTable({ records, onAction }) {
  const [actionNote, setActionNote] = useState('')
  const [actingId, setActingId] = useState(null)

  const act = async (id, action) => {
    setActingId(id)
    if (action === 'approve') await approveRecord(id, 'analyst', actionNote)
    else await rejectRecord(id, 'analyst', actionNote)
    setActingId(null)
    setActionNote('')
    onAction()
  }

  if (!records.length) return <div style={{ color: '#aaa', padding: 32, textAlign: 'center' }}>No records found.</div>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#f9f9f9', borderBottom: '2px solid #eee' }}>
            {['Date', 'Source', 'Scope', 'Category', 'Quantity', 'Unit', 'Location', 'Flags', 'Status', 'Actions'].map(h => (
              <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#555', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map(rec => (
            <tr key={rec.id} style={{ borderBottom: '1px solid #f0f0f0' }}
              onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
              onMouseLeave={e => e.currentTarget.style.background = ''}>
              <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>{rec.activity_date}</td>
              <td style={{ padding: '8px 12px' }}><Badge label={rec.batch_source} color="#7f8c8d" /></td>
              <td style={{ padding: '8px 12px' }}><Badge label={`Scope ${rec.scope}`} color={SCOPE_COLORS[rec.scope]} /></td>
              <td style={{ padding: '8px 12px', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>{rec.category}</td>
              <td style={{ padding: '8px 12px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                {parseFloat(rec.quantity).toLocaleString()}
              </td>
              <td style={{ padding: '8px 12px', color: '#888' }}>{rec.unit}</td>
              <td style={{ padding: '8px 12px', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', color: '#666' }}>{rec.location || '—'}</td>
              <td style={{ padding: '8px 12px' }}>
                {rec.flags && rec.flags.length > 0
                  ? <span title={rec.flags.join(', ')} style={{ color: '#e67e22', cursor: 'help', fontSize: 12 }}>
                      ⚠ {rec.flags.length}
                    </span>
                  : <span style={{ color: '#ccc' }}>—</span>}
              </td>
              <td style={{ padding: '8px 12px' }}>
                <Badge label={rec.review_status} color={STATUS_COLORS[rec.review_status]} />
              </td>
              <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                {rec.is_locked
                  ? <span style={{ color: '#aaa', fontSize: 11 }}>🔒 locked</span>
                  : rec.review_status === 'pending' || rec.review_status === 'suspicious'
                    ? <div style={{ display: 'flex', gap: 4 }}>
                        <button disabled={actingId === rec.id}
                          onClick={() => act(rec.id, 'approve')}
                          style={{ padding: '3px 8px', background: '#27ae60', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                          ✓ Approve
                        </button>
                        <button disabled={actingId === rec.id}
                          onClick={() => act(rec.id, 'reject')}
                          style={{ padding: '3px 8px', background: '#e74c3c', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                          ✗ Reject
                        </button>
                      </div>
                    : <span style={{ color: '#aaa', fontSize: 11 }}>reviewed</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('review')
  const [summary, setSummary] = useState(null)
  const [records, setRecords] = useState([])
  const [batches, setBatches] = useState([])
  const [filters, setFilters] = useState({})
  const [loading, setLoading] = useState(false)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [s, r, b] = await Promise.all([fetchSummary(), fetchRecords(filters), fetchBatches()])
      setSummary(s)
      setRecords(r.results || [])
      setBatches(b)
    } catch (e) { console.error(e) }
    setLoading(false)
  }, [filters])

  useEffect(() => { loadAll() }, [loadAll])

  const tabs = [
    { key: 'review', label: '📋 Review Dashboard' },
    { key: 'upload', label: '⬆ Upload Data' },
    { key: 'batches', label: '📦 Batches' },
  ]

  return (
    <div style={{ minHeight: '100vh', background: '#f4f6f8', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div style={{ background: '#fff', borderBottom: '1px solid #e8e8e8', padding: '0 32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: 1400, margin: '0 auto' }}>
          <div style={{ padding: '16px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 32, height: 32, background: '#16a34a', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: '#fff', fontWeight: 700, fontSize: 14 }}>B</span>
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>Breathe ESG</div>
              <div style={{ fontSize: 11, color: '#888' }}>Data Ingestion & Review Platform</div>
            </div>
          </div>
          <nav style={{ display: 'flex', gap: 0 }}>
            {tabs.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '20px 16px', fontSize: 13, fontWeight: tab === t.key ? 600 : 400,
                color: tab === t.key ? '#16a34a' : '#666',
                borderBottom: tab === t.key ? '2px solid #16a34a' : '2px solid transparent',
                transition: 'all 0.15s'
              }}>{t.label}</button>
            ))}
          </nav>
        </div>
      </div>

      <div style={{ maxWidth: 1400, margin: '0 auto', padding: 32 }}>

        {/* Summary cards */}
        {summary && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
            <StatCard label="Total records" value={summary.total} />
            <StatCard label="Pending review" value={summary.pending} color="#95a5a6" />
            <StatCard label="Suspicious" value={summary.suspicious} color="#e67e22" />
            <StatCard label="Approved" value={summary.approved} color="#27ae60" />
            <StatCard label="Rejected" value={summary.rejected} color="#e74c3c" />
            <StatCard label="Scope 1 (direct)" value={summary.by_scope?.scope_1 || 0} color="#e74c3c" />
            <StatCard label="Scope 2 (electricity)" value={summary.by_scope?.scope_2 || 0} color="#3498db" />
            <StatCard label="Scope 3 (value chain)" value={summary.by_scope?.scope_3 || 0} color="#f39c12" />
          </div>
        )}

        {/* Upload tab */}
        {tab === 'upload' && (
          <div>
            <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 600 }}>Upload data files</h2>
            <UploadPanel onUploaded={loadAll} />
            <div style={{ marginTop: 24, padding: 16, background: '#fff8e1', borderRadius: 8, border: '1px solid #ffe082', fontSize: 12, color: '#7c5e00' }}>
              <strong>Sample files to try:</strong> Download the sample files from the repo's <code>sample_data/</code> folder and upload them here.
              SAP expects CSV, Utility expects CSV, Travel expects JSON.
            </div>
          </div>
        )}

        {/* Review tab */}
        {tab === 'review' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Review & approve records</h2>
              <button onClick={loadAll} style={{
                padding: '6px 14px', background: '#16a34a', color: '#fff',
                border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13
              }}>↻ Refresh</button>
            </div>

            {/* Filters */}
            <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
              {[
                { key: 'review_status', label: 'Status', options: [['', 'All statuses'], ['pending','Pending'], ['suspicious','Suspicious'], ['approved','Approved'], ['rejected','Rejected']] },
                { key: 'source', label: 'Source', options: [['', 'All sources'], ['sap','SAP'], ['utility','Utility'], ['travel','Travel']] },
                { key: 'scope', label: 'Scope', options: [['', 'All scopes'], ['1','Scope 1'], ['2','Scope 2'], ['3','Scope 3']] },
              ].map(f => (
                <select key={f.key} value={filters[f.key] || ''} onChange={e => setFilters(prev => ({ ...prev, [f.key]: e.target.value }))}
                  style={{ padding: '6px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, background: '#fff' }}>
                  {f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              ))}
            </div>

            {loading ? <div style={{ color: '#aaa', padding: 32 }}>Loading…</div>
              : <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e8e8e8' }}>
                  <RecordTable records={records} onAction={loadAll} />
                </div>}
          </div>
        )}

        {/* Batches tab */}
        {tab === 'batches' && (
          <div>
            <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 600 }}>Ingestion batches</h2>
            <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #e8e8e8', overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9f9f9', borderBottom: '2px solid #eee' }}>
                    {['Filename', 'Source', 'Status', 'Rows', 'Errors', 'Uploaded at'].map(h => (
                      <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: '#555' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {batches.map(b => (
                    <tr key={b.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '10px 16px', fontFamily: 'monospace', fontSize: 12 }}>{b.filename}</td>
                      <td style={{ padding: '10px 16px' }}><Badge label={b.source} color="#7f8c8d" /></td>
                      <td style={{ padding: '10px 16px' }}>
                        <Badge label={b.status} color={b.status === 'done' ? '#27ae60' : b.status === 'failed' ? '#e74c3c' : '#95a5a6'} />
                      </td>
                      <td style={{ padding: '10px 16px' }}>{b.row_count}</td>
                      <td style={{ padding: '10px 16px', color: b.error_count > 0 ? '#e74c3c' : '#aaa' }}>{b.error_count}</td>
                      <td style={{ padding: '10px 16px', color: '#888', fontSize: 12 }}>{new Date(b.uploaded_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
