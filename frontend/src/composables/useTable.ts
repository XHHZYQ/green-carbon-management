import { reactive, shallowRef } from 'vue'
import type { PageResult } from '@/types'

type Query = Record<string, any>

/**
 * 列表分页通用逻辑，返回 reactive 状态，模板中直接使用（无需 .value）。
 * @param fetcher 列表接口
 * @param defaultQuery 默认查询条件
 */
export function useTable<T>(fetcher: (params: Query) => Promise<PageResult<T>>, defaultQuery: Query = {}) {
  const loading = shallowRef(false)
  const list = shallowRef<T[]>([])
  const total = shallowRef(0)
  const query = reactive<Query>({ page: 1, page_size: 10, ...defaultQuery })

  async function load() {
    loading.value = true
    try {
      const res = await fetcher({ ...query })
      list.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  function search() {
    query.page = 1
    return load()
  }

  function reset() {
    Object.assign(query, { page: 1, page_size: 10 }, defaultQuery)
    return load()
  }

  function changePage(page: number) {
    query.page = page
    return load()
  }

  function changeSize(pageSize: number) {
    query.page_size = pageSize
    query.page = 1
    return load()
  }

  return reactive({
    loading,
    list,
    total,
    query,
    load,
    search,
    reset,
    changePage,
    changeSize,
  })
}
