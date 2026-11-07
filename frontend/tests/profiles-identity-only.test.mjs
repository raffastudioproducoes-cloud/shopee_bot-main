import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")

test("Cards mostram apenas foto e nome, com ações no menu", () => {
  const card = read("../src/components/profiles/ProfileCard.tsx")
  assert.match(card, /<Avatar name=\{profile\.nome\}/)
  assert.match(card, /profile-card__name/)
  assert.match(card, /Opções do perfil/)
  assert.match(card, /onActivate/)
  assert.doesNotMatch(card, /profile\.email|profile\.telefone|profile\.endereco|<PlanBadge|<Badge|kindLabel/)
  assert.doesNotMatch(card, />Ativo<|>Em uso<|>Ativar</)
})

test("Novo/editar perfil pedem somente nome e foto, sem dados da conta", () => {
  const form = read("../src/components/profiles/ProfileFormModal.tsx")
  assert.match(form, /Nome do perfil \*/)
  assert.match(form, /Foto do perfil \(opcional\)/)
  assert.match(form, /onSubmit\(\{ nome: nome\.trim\(\) \}, avatar/)
  assert.doesNotMatch(form, /TextInput label="E-mail|TextInput label="Telefone|TextInput label="Endereço/)
  const page = read("../src/pages/ProfilesPage.tsx")
  assert.doesNotMatch(page, /<PlanBadge/)
  assert.match(page, /resource="profiles"/)
  const profileApi = read("../src/api/profiles.ts")
  assert.match(profileApi, /interface ProfileInput \{\s*nome: string\s*\}/)
})
