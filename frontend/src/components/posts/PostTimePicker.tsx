import { useId } from "react"
import { getUserTimeZone } from "../../lib/userTimeZone"
import "./postTimePicker.css"

interface Props {
  label: string
  value: string
  onChange: (value: string) => void
}

const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"))
const MINUTES = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0"))
const PRESETS = ["09:00", "12:00", "15:00", "18:00", "21:00"]

/**
 * No desktop, campos de hora/minuto 24h evitam o popup nativo do Windows
 * (12h/AM-PM, deslocado e difícil de navegar). Android mantém o seletor
 * nativo, que já é adequado para toque.
 */
export function PostTimePicker({ label, value, onChange }: Props) {
  const id = useId()
  const [hour = "09", minute = "00"] = value.split(":")
  const setHour = (next: string) => onChange(`${next}:${MINUTES.includes(minute) ? minute : "00"}`)
  const setMinute = (next: string) => onChange(`${HOURS.includes(hour) ? hour : "09"}:${next}`)

  return (
    <div className="post-time-picker">
      <span id={id} className="post-time-picker-label">{label} <small>({getUserTimeZone()}, 24h)</small></span>
      <div className="post-time-picker-desktop" role="group" aria-labelledby={id}>
        <label>
          <span className="post-time-picker-sr">Horas</span>
          <select aria-label={`${label}: horas`} value={HOURS.includes(hour) ? hour : "09"} onChange={(e) => setHour(e.target.value)}>
            {HOURS.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <span className="post-time-picker-colon" aria-hidden="true">:</span>
        <label>
          <span className="post-time-picker-sr">Minutos</span>
          <select aria-label={`${label}: minutos`} value={MINUTES.includes(minute) ? minute : "00"} onChange={(e) => setMinute(e.target.value)}>
            {MINUTES.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <div className="post-time-picker-presets" aria-label="Horários rápidos">
          {PRESETS.map((preset) => <button key={preset} type="button" aria-pressed={value === preset}
            onClick={() => onChange(preset)}>{preset}</button>)}
        </div>
      </div>
      <input className="post-time-picker-touch" aria-label={label} type="time" step={60}
        value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}
