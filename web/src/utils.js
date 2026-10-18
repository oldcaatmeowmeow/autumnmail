export function parseDate(value) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function fmtDate(value) {
  const date = parseDate(value)
  if (!date) return '待定'
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

export function fmtDateTime(value) {
  const date = parseDate(value)
  if (!date) return '待定'
  return `${date.getMonth() + 1}月${date.getDate()}日 ${fmtTime(date)}`
}

export function fmtTime(value) {
  const date = value instanceof Date ? value : parseDate(value)
  if (!date) return '--:--'
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function dayNum(value) {
  const date = parseDate(value)
  return date ? String(date.getDate()).padStart(2, '0') : '--'
}

export function monthShort(value) {
  const date = parseDate(value)
  return date ? `${date.getMonth() + 1}月` : ''
}

export function dateKey(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

export function isToday(value) {
  const date = parseDate(value)
  if (!date) return false
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

export function timeAgo(value) {
  const date = parseDate(value)
  if (!date) return ''
  const diff = Date.now() - date.getTime()
  const minutes = Math.round(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days} 天前`
  return fmtDate(value)
}

export function categoryTone(category = '') {
  if (category.includes('拒')) return 'reject'
  if (category.includes('Offer') || category.includes('录用')) return 'offer'
  if (category.includes('测评') || category.includes('笔试')) return 'assessment'
  if (category.includes('面')) return 'interview'
  return 'info'
}

export function statusTone(status = '') {
  if (status === '已拒绝') return 'reject'
  if (status === '已Offer') return 'offer'
  if (status === '面试中') return 'interview'
  if (status === '测评中') return 'assessment'
  return 'info'
}
