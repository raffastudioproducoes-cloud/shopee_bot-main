/**
 * Produtos reais do catálogo do dono do produto (conta rafastudio, 09/11/2026), usados como exemplo
 * nas animações da apresentação. Dados estáticos escolhidos à mão: a página pública nunca consulta
 * o banco, e daqui saem só nome curto, preço e imagem. Nada de link de afiliado nem de outra conta.
 * `from` indica que o preço é o menor entre as variações ("a partir de").
 */
export interface DemoProduct {
  id: number
  name: string
  price: number
  from: boolean
  image: string
}

const CDN = "https://cf.shopee.com.br/file/"

export const demoProducts: DemoProduct[] = [
  { id: 49, name: "Smartwatch F9 2026 com Bluetooth e chamadas", price: 78.6, from: true, image: `${CDN}br-11134207-81z1k-mh33kjyuqxvrc5` },
  { id: 51, name: "Organizador de ovos anti-queda para geladeira", price: 4.99, from: true, image: `${CDN}sg-11134201-81zvu-mmvetjba5xq9cb` },
  { id: 66, name: "Armário espelheira com porta Cleo", price: 139.99, from: false, image: `${CDN}br-11134207-81z1k-mgpg7k9uadc4fb` },
  { id: 57, name: "Espelho Flame com moldura em couro orgânico", price: 49, from: true, image: `${CDN}br-11134207-820m8-ms35tbxdrqiu49` },
  { id: 60, name: "Estante de ferro reforçada 300 kg", price: 134.9, from: true, image: `${CDN}br-11134207-81ztc-mkjb15xby9kze0` },
  { id: 58, name: "Cortina blackout 2,20 m × 1,30 m", price: 30.9, from: true, image: `${CDN}br-11134207-820ls-mspjdyc2m1olcf` },
  { id: 59, name: "Painel ripado autoadesivo 3D amadeirado", price: 79.8, from: false, image: `${CDN}br-11134207-81zug-mkwz5xpqeio1dd` },
  { id: 52, name: "Kit 5 suportes organizadores de parede", price: 13.98, from: false, image: `${CDN}sg-11134201-825ao-mtvyz2337if8c6` },
]

export function formatDemoPrice(product: DemoProduct): string {
  const value = product.price.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
  return product.from ? `a partir de ${value}` : value
}

/** Texto de exemplo do editor (publicação real do catálogo do dono, sem o link). */
export const demoPostText =
  "Chega de ovos quebrados! 🥚 O organizador anti-queda que todo mundo está usando otimiza sua geladeira com total praticidade. Garanta o seu!"
