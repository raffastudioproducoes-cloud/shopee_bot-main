import type { ChangeEvent, ReactNode, CSSProperties } from "react"
import { SearchField } from "./SearchField"
import { IconButton } from "./IconButton"

/**
 * App top bar — search pill, notification bell, account avatar.
 */
export interface TopBarProps {
  query?: string
  onQuery?: (e: ChangeEvent<HTMLInputElement>) => void
  /** Avatar image path. */
  avatarSrc?: string
  searchWidth?: number
  onBell?: () => void
  /** Red dot on the bell. Ignored when `bell` overrides the default button. */
  unread?: boolean
  /** Node before the search pill (mobile puts the avatar here). */
  leading?: ReactNode
  /** Node before the bell. */
  trailing?: ReactNode
  /** Replaces the default bell IconButton entirely (e.g. a self-contained
   *  notifications dropdown) — `onBell`/`unread` are ignored when set. */
  bell?: ReactNode
  className?: string
  style?: CSSProperties
}

/** Search pill left, notifications + avatar right. */
export function TopBar({
  query = "",
  onQuery,
  avatarSrc,
  searchWidth = 220,
  onBell,
  unread = true,
  leading,
  trailing,
  bell,
  className = "",
  style,
}: TopBarProps) {
  return (
    <header
      className={`app-topbar ${className}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        minHeight: "var(--topbar-h)",
        ...style,
      }}
    >
      {leading}
      <SearchField value={query} onChange={onQuery} width={searchWidth} className="app-topbar-search" />
      <span style={{ flex: 1 }} />
      {trailing}
      {bell ?? <IconButton icon="bell" label="Notifications" tone="glass" badge={unread} onClick={onBell} />}
      {avatarSrc ? (
        <img
          src={avatarSrc}
          alt="Account"
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            objectFit: "cover",
            display: "block",
            border: "1px solid var(--border-hairline)",
          }}
        />
      ) : null}
    </header>
  )
}
