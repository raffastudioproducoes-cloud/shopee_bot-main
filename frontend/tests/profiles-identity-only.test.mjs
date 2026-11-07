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

test("O card principal contém os dados editáveis e os secundários mantêm só nome/foto", () => {
  const page = read("../src/pages/ProfilesPage.tsx")
  const card = read("../src/components/profiles/ProfileCard.tsx")
  const identity = read("../src/components/profiles/AccountIdentityForm.tsx")

  assert.match(page, /principalProfile = profiles\.find\(profile => profile\.kind === "principal"\)/)
  assert.match(page, /secondaryProfiles = profiles\.filter\(profile => profile\.kind !== "principal"\)/)
  assert.match(page, /profileCard\(principalProfile, primaryDetails\)/)
  assert.match(page, /secondaryProfiles\.map\(profile => profileCard\(profile\)\)/)
  assert.match(page, /const primaryNotices = <>[\s\S]*<ResourceQuotaBar[\s\S]*<AccountIdentityIntro \/>[\s\S]*<\/>/)
  assert.match(page, /const primaryDetails = <AccountIdentityForm \/>/)
  assert.match(page, /<div className="profiles-primary-stack">[\s\S]*\{primaryNotices\}[\s\S]*profileCard\(principalProfile, primaryDetails\)/)
  assert.match(card, /isPrincipal && children && <div className="profile-card__details">\{children\}<\/div>/)
  assert.match(identity, /return <section className="account-identity"/)
  assert.doesNotMatch(identity, /<Panel/)
  assert.match(identity, /<form onSubmit=\{handleSubmit\}>/)
  assert.match(identity, /Salvar dados cadastrais/)
})

test("Desktop organiza card principal à esquerda e perfis adicionais em coluna à direita; celular empilha", () => {
  const page = read("../src/pages/ProfilesPage.tsx")
  const styles = read("../src/components/profiles/profileCard.css")
  assert.match(page, /profiles-cards--with-secondary/)
  assert.match(page, /secondaryProfiles\.length > 0/)
  assert.match(styles, /\.profiles-cards\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/)
  assert.match(styles, /\.profiles-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/)
  assert.match(styles, /@media \(min-width: 1000px\)\s*\{\s*\.profiles-cards--with-secondary\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) minmax\(240px, 320px\)/)
  assert.match(styles, /\.profiles-cards--with-secondary > \.profiles-grid\s*\{[^}]*grid-column:\s*2;\s*grid-row:\s*1/)
})
