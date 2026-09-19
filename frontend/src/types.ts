export type RoomStatus = 'fruiting' | 'idle' | 'sanitize'
export type HarvestGrade = 'A' | 'B' | 'C'
export type SanitizeMethod = 'uv' | 'chemical'
export type SanitizeStatus = 'open' | 'doing' | 'done' | 'void'

export interface Shed {
  id: number
  name: string
  location: string
  notes?: string | null
}

export interface Room {
  id: number
  shedId: number
  roomCode: string
  species: string
  capacityBags: number
  status: RoomStatus
  activeSanitizeOrderId?: number | null
}

export interface ClimateLog {
  id: number
  roomId: number
  recordedAt: string
  tempC: number
  humidityPct: number
  co2Ppm?: number | null
  notes?: string | null
}

export interface FlushHarvest {
  id: number
  roomId: number
  harvestedAt: string
  flushNo: number
  weightKg: number
  grade: HarvestGrade
  operatorName: string
}

export interface SanitizeOrder {
  id: number
  roomId: number
  method: SanitizeMethod
  status: SanitizeStatus
  operatorName: string
  plannedAt: string
  startedAt?: string | null
  finishedAt?: string | null
}

export interface DashboardStats {
  shedTotal: number
  fruitingRoomCount: number
  climateLast24h: number
  harvestKgLast7d: number
}
