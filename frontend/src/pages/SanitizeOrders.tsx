import { createSignal, onMount } from 'solid-js'
import { For, Show } from 'solid-js'
import { api } from '../api/client'
import type { Room, SanitizeMethod, SanitizeOrder, SanitizeStatus } from '../types'

const methods: SanitizeMethod[] = ['uv', 'chemical']

const methodLabels: Record<SanitizeMethod, string> = {
  uv: '紫外',
  chemical: '化学',
}

const statusLabels: Record<SanitizeStatus, string> = {
  open: '待开始',
  doing: '消杀中',
  done: '已完工',
  void: '已作废',
}

function toLocalInput(iso?: string) {
  const d = iso ? new Date(iso) : new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fmt(iso?: string | null) {
  return iso ? new Date(iso).toLocaleString() : '—'
}

const empty = {
  roomId: '',
  method: 'uv' as SanitizeMethod,
  operatorName: '',
  plannedAt: toLocalInput(),
}

export default function SanitizeOrders() {
  const [rows, setRows] = createSignal<SanitizeOrder[]>([])
  const [rooms, setRooms] = createSignal<Room[]>([])
  const [form, setForm] = createSignal({ ...empty })
  const [error, setError] = createSignal('')

  async function load() {
    const [orders, roomList] = await Promise.all([
      api<SanitizeOrder[]>('/api/sanitize-orders'),
      api<Room[]>('/api/rooms'),
    ])
    setRows(orders)
    setRooms(roomList)
  }

  onMount(() => {
    load().catch((e) => setError(e.message))
  })

  function roomLabel(roomId: number) {
    const r = rooms().find((x) => x.id === roomId)
    return r ? `${r.roomCode} · ${r.species}` : `#${roomId}`
  }

  async function onSubmit(e: Event) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/sanitize-orders', {
        method: 'POST',
        body: JSON.stringify({
          roomId: Number(form().roomId),
          method: form().method,
          operatorName: form().operatorName,
          plannedAt: new Date(form().plannedAt).toISOString(),
        }),
      })
      setForm({ ...empty, plannedAt: toLocalInput() })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function transition(id: number, to: SanitizeStatus) {
    setError('')
    try {
      await api(`/api/sanitize-orders/${id}/transition`, {
        method: 'POST',
        body: JSON.stringify({ to }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '流转失败')
    }
  }

  return (
    <div>
      <header class="page-header">
        <h1>消杀单</h1>
        <p class="muted">
          状态机 open → doing → done，非终态可 void；开工强制房态为 sanitize，完工需消杀期间环境记录
        </p>
      </header>
      {error() && <div class="error">{error()}</div>}

      <form class="panel form-grid" onSubmit={onSubmit}>
        <label>
          出菇室
          <select
            value={form().roomId}
            onChange={(e) => setForm({ ...form(), roomId: e.currentTarget.value })}
            required
          >
            <option value="">选择出菇室</option>
            <For each={rooms()}>
              {(r) => (
                <option value={String(r.id)} disabled={r.activeSanitizeOrderId != null}>
                  {r.roomCode} · {r.species}
                  {r.activeSanitizeOrderId != null ? '（已有开放消杀单）' : ''}
                </option>
              )}
            </For>
          </select>
        </label>
        <label>
          消杀方式
          <select
            value={form().method}
            onChange={(e) =>
              setForm({ ...form(), method: e.currentTarget.value as SanitizeMethod })
            }
          >
            <For each={methods}>{(m) => <option value={m}>{methodLabels[m]}</option>}</For>
          </select>
        </label>
        <label>
          操作人
          <input
            value={form().operatorName}
            onInput={(e) => setForm({ ...form(), operatorName: e.currentTarget.value })}
            required
          />
        </label>
        <label>
          计划时间
          <input
            type="datetime-local"
            value={form().plannedAt}
            onInput={(e) => setForm({ ...form(), plannedAt: e.currentTarget.value })}
            required
          />
        </label>
        <button type="submit" class="btn primary">
          新建消杀单
        </button>
      </form>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>出菇室</th>
              <th>方式</th>
              <th>状态</th>
              <th>操作人</th>
              <th>计划时间</th>
              <th>开始时间</th>
              <th>完成时间</th>
              <th>流转</th>
            </tr>
          </thead>
          <tbody>
            <For each={rows()}>
              {(o) => (
                <tr>
                  <td>{o.id}</td>
                  <td>{roomLabel(o.roomId)}</td>
                  <td>{methodLabels[o.method]}</td>
                  <td>
                    <span class={`badge so-${o.status}`}>{statusLabels[o.status]}</span>
                  </td>
                  <td>{o.operatorName}</td>
                  <td>{fmt(o.plannedAt)}</td>
                  <td>{fmt(o.startedAt)}</td>
                  <td>{fmt(o.finishedAt)}</td>
                  <td>
                    <div class="row-actions">
                      <Show when={o.status === 'open'}>
                        <button
                          type="button"
                          class="btn ghost"
                          onClick={() => transition(o.id, 'doing')}
                        >
                          开始
                        </button>
                      </Show>
                      <Show when={o.status === 'doing'}>
                        <button
                          type="button"
                          class="btn ghost"
                          onClick={() => transition(o.id, 'done')}
                        >
                          完工
                        </button>
                      </Show>
                      <Show when={o.status === 'open' || o.status === 'doing'}>
                        <button
                          type="button"
                          class="btn ghost"
                          onClick={() => transition(o.id, 'void')}
                        >
                          作废
                        </button>
                      </Show>
                      <Show when={o.status === 'done' || o.status === 'void'}>
                        <span class="hint">终态</span>
                      </Show>
                    </div>
                  </td>
                </tr>
              )}
            </For>
          </tbody>
        </table>
      </div>
    </div>
  )
}
