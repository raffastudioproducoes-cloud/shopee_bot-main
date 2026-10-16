export function clampZoom(value: number) { return Math.min(3, Math.max(1, value)) }

export function wheelGlobeZoom(zoom: number, deltaY: number, deltaMode = 0) {
  const pixels = deltaY * (deltaMode === 1 ? 16 : deltaMode === 2 ? 500 : 1)
  return clampZoom(zoom * Math.exp(-Math.max(-240, Math.min(240, pixels)) * .0018))
}

export function earthRotation(longitude: number, elapsedMs: number) {
  // Rotação ilustrativa oeste→leste; uma volta em cerca de 6m40s.
  return ((longitude - Math.max(0, Math.min(100, elapsedMs)) * .0009 + 540) % 360) - 180
}

export function projectGlobe(longitude: number, latitude: number, centerLongitude: number, centerLatitude: number, zoom = 1, tilt = 0) {
  const rad = Math.PI / 180
  const lat = latitude * rad
  const center = centerLatitude * rad
  const delta = (longitude - centerLongitude) * rad
  const depth = Math.sin(center) * Math.sin(lat) + Math.cos(center) * Math.cos(lat) * Math.cos(delta)
  const x = 200 * zoom * Math.cos(lat) * Math.sin(delta)
  const y = -200 * zoom * (Math.cos(center) * Math.sin(lat) - Math.sin(center) * Math.cos(lat) * Math.cos(delta))
  const roll = tilt * rad
  return {
    x: 320 + x * Math.cos(roll) - y * Math.sin(roll),
    y: 250 + x * Math.sin(roll) + y * Math.cos(roll),
    visible: depth > 0, depth,
  }
}
