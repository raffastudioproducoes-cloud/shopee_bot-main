import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { adminCredentialsApi } from '../../api/credentialsAdmin'
import { Panel } from '../ui/Panel'
import { Button } from '../ui/Button'
import { TextInput } from '../ui/TextInput'

type Banner = { ok: boolean; text: string } | null
type OverrideKind = 'threads' | 'x' | 'facebook' | 'tiktok' | 'instagram' | 'kwai'

const PORTALS: Record<OverrideKind, string> = {
  threads: 'https://developers.facebook.com/docs/threads',
  x: 'https://developer.x.com/',
  facebook: 'https://developers.facebook.com/',
  tiktok: 'https://developers.tiktok.com/',
  instagram: 'https://developers.facebook.com/',
  kwai: 'https://developer.kwai.com/',
}

const LABELS: Record<OverrideKind, string> = {
  threads: 'Threads',
  x: 'X',
  facebook: 'Facebook',
  tiktok: 'TikTok',
  instagram: 'Instagram',
  kwai: 'Kwai',
}

const FIELDS: Record<OverrideKind, Array<{ key: string; label: string; secret?: boolean; optional?: boolean }>> = {
  threads: [{ key: 'userId', label: 'Threads User ID' }, { key: 'accessToken', label: 'Access Token', secret: true }],
  x: [{ key: 'accessToken', label: 'Access Token', secret: true }, { key: 'refreshToken', label: 'Refresh Token (opcional)', secret: true, optional: true }],
  facebook: [{ key: 'pageId', label: 'Page ID' }, { key: 'accessToken', label: 'Page Access Token', secret: true }, { key: 'pageName', label: 'Page Name (opcional)', optional: true }],
  tiktok: [{ key: 'openId', label: 'Open ID' }, { key: 'accessToken', label: 'Access Token', secret: true }, { key: 'refreshToken', label: 'Refresh Token (opcional)', secret: true, optional: true }],
  instagram: [{ key: 'igUserId', label: 'Instagram User ID' }, { key: 'accessToken', label: 'Access Token', secret: true }],
  kwai: [{ key: 'appId', label: 'App ID' }, { key: 'secret', label: 'Secret', secret: true }],
}

const GRID = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 } as const

export function AdminOverrides({ onSaved, onAuthError, setBanner }: {
  onSaved: () => void
  onAuthError: (error: Error) => void
  setBanner: (banner: Banner) => void
}) {
  return (
    <section aria-label="Opções administrativas" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <h2 style={{ font: 'var(--text-role-title)', color: 'var(--text-display)', margin: 0 }}>Opções administrativas</h2>
        <p style={{ color: 'var(--text-muted)', margin: '4px 0 0' }}>Overrides manuais para diagnóstico e testes do aplicativo.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: 16 }}>
        {(Object.keys(LABELS) as OverrideKind[]).map((network) => (
          <ManualOverrideCard key={network} network={network} onSaved={onSaved} onAuthError={onAuthError} setBanner={setBanner} />
        ))}
      </div>
    </section>
  )
}

function ManualOverrideCard({ network, onSaved, onAuthError, setBanner }: {
  network: OverrideKind
  onSaved: () => void
  onAuthError: (error: Error) => void
  setBanner: (banner: Banner) => void
}) {
  const [values, setValues] = useState<Record<string, string>>({})
  const fields = FIELDS[network]
  const save = useMutation({
    mutationFn: () => {
      const value = (key: string) => values[key] ?? ''
      switch (network) {
        case 'threads': return adminCredentialsApi.saveThreads(value('userId'), value('accessToken'))
        case 'x': return adminCredentialsApi.saveX(value('accessToken'), value('refreshToken') || undefined)
        case 'facebook': return adminCredentialsApi.saveFacebook(value('pageId'), value('accessToken'), value('pageName') || undefined)
        case 'tiktok': return adminCredentialsApi.saveTikTok(value('openId'), value('accessToken'), value('refreshToken') || undefined)
        case 'instagram': return adminCredentialsApi.saveInstagram(value('igUserId'), value('accessToken'))
        case 'kwai': return adminCredentialsApi.saveKwai(value('appId'), value('secret'))
      }
    },
    onSuccess: () => {
      setValues({})
      setBanner({ ok: true, text: `${LABELS[network]} salvo. Testando a conexão...` })
      onSaved()
    },
    onError: onAuthError,
  })

  const canSave = fields.filter((field) => !field.optional).every((field) => values[field.key]?.trim())
  return (
    <Panel surface="dark" style={{ padding: 16 }}>
      <form onSubmit={(event) => { event.preventDefault(); save.mutate() }} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
          <strong>{LABELS[network]}</strong>
          <a href={PORTALS[network]} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-500)', font: 'var(--text-role-body)' }}>
            Portal de desenvolvedores
          </a>
        </div>
        <div style={GRID}>
          {fields.map((field) => (
            <TextInput
              key={field.key}
              label={field.label}
              type={field.secret ? 'password' : 'text'}
              value={values[field.key] ?? ''}
              onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}
              autoComplete="off"
              required={!field.optional}
            />
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="primary" disabled={save.isPending || !canSave}>
            {save.isPending ? 'Salvando...' : 'Salvar override'}
          </Button>
        </div>
      </form>
    </Panel>
  )
}
