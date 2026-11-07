import { useEffect, useState } from "react"
import {
  DEFAULT_PHONE_COUNTRY, PHONE_COUNTRIES, internationalPhone,
  maskNationalPhone, parseStoredPhone,
} from "../../lib/phone"

type PhoneInputProps = {
  label: string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  mobile?: boolean
}

/** Dois controles acessíveis, mas um único valor internacional no formulário. */
export function PhoneInput({ label, value, onChange, disabled, mobile = false }: PhoneInputProps) {
  const [countryId, setCountryId] = useState(() => parseStoredPhone(value).country.id)
  useEffect(() => {
    if (value.startsWith("+")) setCountryId(parseStoredPhone(value).country.id)
  }, [value])

  const country = PHONE_COUNTRIES.find(item => item.id === countryId) ?? DEFAULT_PHONE_COUNTRY
  const parsed = parseStoredPhone(value)
  const national = value.startsWith("+") && parsed.country.id !== country.id ? "" : parsed.national

  const updateNumber = (input: string) => {
    if (input.trim().startsWith("+")) {
      const pasted = parseStoredPhone(input)
      setCountryId(pasted.country.id)
      onChange(internationalPhone(pasted.country, pasted.national))
    } else {
      onChange(internationalPhone(country, input))
    }
  }

  return <div className="account-phone">
    <span className="csp-s-0142">{label}</span>
    <div className="account-phone__row">
      <select className="account-phone__country" aria-label={`Código do país — ${label}`}
        title="Ao trocar o país, informe o número novamente" disabled={disabled} value={country.id}
        onChange={event => { setCountryId(event.target.value); onChange("") }}>
        {PHONE_COUNTRIES.map(item => <option key={item.id} value={item.id}>{item.name} (+{item.dial})</option>)}
      </select>
      <input className="account-phone__number" type="tel" inputMode="tel" autoComplete="tel-national"
        aria-label={`Número — ${label}`} disabled={disabled} maxLength={24}
        value={maskNationalPhone(country, national, mobile)}
        placeholder={country.id === "BR" ? (mobile ? "(21) 99999-9999" : "(21) 9999-9999") : "Número de telefone"}
        onChange={event => updateNumber(event.target.value)} />
    </div>
  </div>
}
