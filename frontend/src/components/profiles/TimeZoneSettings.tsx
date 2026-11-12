import { useMemo, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { authApi } from "../../api/auth"
import { Panel } from "../ui/Panel"
import { Button } from "../ui/Button"
import { Select } from "../ui/Select"
import { deviceTimeZone, getUserTimeZone, setUserTimeZone, supportedTimeZones } from "../../lib/userTimeZone"

/** Fuso usado para agendar e exibir horários. Agendas já criadas mantêm o fuso delas. */
export function TimeZoneSettings() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState(getUserTimeZone)
  const zones = useMemo(supportedTimeZones, [])
  const device = deviceTimeZone()
  const save = useMutation({
    mutationFn: (zone: string) => authApi.updateTimeZone(zone),
    onSuccess: ({ timezone }) => {
      setUserTimeZone(timezone)
      setSelected(timezone)
      // Refaz as telas para mostrarem os horários no fuso novo.
      queryClient.invalidateQueries()
    },
  })

  return (
    <Panel padding={24} style={{ maxWidth: 420 }}>
      <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>Fuso horário</h2>
      <p style={{ margin: "0 0 12px" }}>
        Horários de agendamento e de exibição usam este fuso. Este dispositivo está em {device}.
        Recorrências já criadas continuam no fuso em que foram agendadas.
      </p>
      <Select label="Fuso (IANA)" value={selected} onChange={(event) => setSelected(event.target.value)}
        options={zones.map((zone) => ({ value: zone, label: zone }))} />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
        <Button type="button" disabled={save.isPending || selected === getUserTimeZone()} onClick={() => save.mutate(selected)}>
          {save.isPending ? "Salvando…" : "Salvar fuso"}
        </Button>
        {device !== selected && (
          <Button type="button" variant="secondary" onClick={() => setSelected(device)}>Usar o deste dispositivo</Button>
        )}
      </div>
      <p role="status" style={{ margin: "8px 0 0", minHeight: 20 }}>
        {save.isError ? "Não foi possível salvar o fuso. Tente de novo." : save.isSuccess ? `Fuso salvo: ${getUserTimeZone()}.` : ""}
      </p>
    </Panel>
  )
}
