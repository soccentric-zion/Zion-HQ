import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import FaultsAlarmsPanel from '../FaultsAlarmsPanel.vue'
import { useAuthStore } from '@/stores/auth'
import type {
  Alarm,
  DeviceAlarm,
  DeviceAlarmListResponse,
  FaultListResponse,
} from '@/lib/types'

// Mock the api module so the panel never hits the network. vi.hoisted runs
// before vi.mock's hoisted factory, so the `api` handle is defined when the
// factory executes and is also accessible to the test bodies below. The
// vi.fn type parameters satisfy oxlint's require-mock-type-parameters rule
// and keep the mock signature aligned with the real api client.
const { api } = vi.hoisted(() => ({
  api: {
    faults: { list: vi.fn<(deviceId: string) => Promise<FaultListResponse>>() },
    alarms: {
      listForDevice: vi.fn<(deviceId: string) => Promise<DeviceAlarmListResponse>>(),
      acknowledge: vi.fn<(id: string) => Promise<Alarm>>(),
      resolve: vi.fn<(id: string) => Promise<Alarm>>(),
      clear: vi.fn<(deviceId: string, alarmId: string) => Promise<DeviceAlarm>>(),
    },
  },
}))

vi.mock('@/lib/api', () => ({ api, ApiError: class ApiError extends Error {} }))

const DEVICE_ID = '11111111-1111-1111-1111-111111111111'
const ALARM_ID = '22222222-2222-2222-2222-222222222222'

function deviceAlarmResponse(): DeviceAlarmListResponse {
  return {
    items: [
      {
        id: ALARM_ID,
        device_id: DEVICE_ID,
        major_id: 1,
        sub_section: 2,
        fault_type: 3,
        severity: 4,
        alarm_code: 0x01020304,
        state: 'active',
        triggered_at: '2026-07-30T12:00:00Z',
        resolved_at: null,
      },
    ],
    page: { total: 1, limit: 100, offset: 0 },
  }
}

function emptyFaults(): FaultListResponse {
  return { items: [], page: { total: 0, limit: 100, offset: 0 } }
}

// Mount the panel with an operator session so the Clear button is visible.
// A single pinia instance is both set active and provided to the app, so the
// auth store mutated here is the same one the component reads in setup.
async function mountAsOperator() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.user = { id: '1', email: 'op@example.com', role: 'operator', created_at: '' }

  const wrapper = mount(FaultsAlarmsPanel, {
    props: { deviceId: DEVICE_ID },
    global: { plugins: [pinia] },
  })
  await flushPromises()
  return wrapper
}

describe('FaultsAlarmsPanel', () => {
  beforeEach(() => {
    api.faults.list.mockReset()
    api.alarms.listForDevice.mockReset()
    api.alarms.acknowledge.mockReset()
    api.alarms.resolve.mockReset()
    api.alarms.clear.mockReset()
    api.faults.list.mockResolvedValue(emptyFaults())
    api.alarms.listForDevice.mockResolvedValue(deviceAlarmResponse())
    api.alarms.clear.mockResolvedValue({
      ...deviceAlarmResponse().items[0],
      state: 'resolved',
      resolved_at: '2026-07-30T12:01:00Z',
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the decoded 4-byte fields and hex alarm_code', async () => {
    const wrapper = await mountAsOperator()

    const html = wrapper.html()
    expect(html).toContain('0x01020304')
    expect(html).toContain('major 1')
    expect(html).toContain('sub 2')
    expect(html).toContain('type 3')
    expect(html).toContain('sev 4')
  })

  it('shows a Clear button for an active alarm (operator) and wires it to api.alarms.clear, then re-loads', async () => {
    const wrapper = await mountAsOperator()

    const clearBtn = wrapper.find('button')
    expect(clearBtn.exists()).toBe(true)
    expect(clearBtn.text()).toContain('Clear')

    await clearBtn.trigger('click')
    await flushPromises()

    expect(api.alarms.clear).toHaveBeenCalledWith(DEVICE_ID, ALARM_ID)
    // clear() resolves -> load() re-fires the list calls.
    expect(api.alarms.listForDevice).toHaveBeenCalledTimes(2)
  })

  it('does not render Acknowledge/Resolve buttons for device alarms', async () => {
    const wrapper = await mountAsOperator()

    const text = wrapper.text()
    expect(text).not.toContain('Acknowledge')
    expect(text).not.toContain('Resolve')
  })
})