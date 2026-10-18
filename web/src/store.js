import { reactive } from 'vue'
import { api } from './api'

export const store = reactive({
  bootstrap: null,
  meta: { version: '0.1.0' },
  loading: true,
  revision: 0,
})

export async function refreshBootstrap() {
  const [bootstrap, meta] = await Promise.all([api.bootstrap(), api.meta()])
  store.bootstrap = bootstrap
  store.meta = meta
  return bootstrap
}

export function bumpRevision() {
  store.revision += 1
}
