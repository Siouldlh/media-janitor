/**
 * Fonctions de filtrage pour les items de plan
 */

export function filterNeverWatched(items) {
  return items.filter(item => item.never_watched === true || item.view_count === 0)
}

export function filterLastWatchedDays(items, days) {
  if (!days || days <= 0) return items
  
  const cutoffDate = new Date()
  cutoffDate.setDate(cutoffDate.getDate() - days)
  
  return items.filter(item => {
    if (!item.last_viewed_at) return true // Jamais vus inclus
    const lastViewed = new Date(item.last_viewed_at)
    return lastViewed < cutoffDate
  })
}

export function filterAddedMonths(items, months) {
  if (!months || months <= 0) return items
  
  const cutoffDate = new Date()
  cutoffDate.setMonth(cutoffDate.getMonth() - months)
  
  return items.filter(item => {
    const addedDate = item.meta?.radarr_added || item.meta?.sonarr_added || item.meta?.added_at
    if (!addedDate) return false
    const added = new Date(addedDate)
    return added < cutoffDate
  })
}

export function filterWithTorrents(items) {
  return items.filter(item => item.qb_hashes && item.qb_hashes.length > 0)
}

export function filterWithoutTorrents(items) {
  return items.filter(item => !item.qb_hashes || item.qb_hashes.length === 0)
}

export function filterProtected(items) {
  return items.filter(item => !!item.protected_reason)
}

export function filterUnprotected(items) {
  return items.filter(item => !item.protected_reason)
}

export function filterByRule(items, rule) {
  if (!rule || rule === 'all') return items
  return items.filter(item => item.rule === rule)
}

export function applyFilters(items, filters) {
  let filtered = [...items]
  
  if (filters.neverWatchedOnly) {
    filtered = filterNeverWatched(filtered)
  }
  
  if (filters.lastWatchedDays && filters.lastWatchedDays > 0) {
    filtered = filterLastWatchedDays(filtered, filters.lastWatchedDays)
  }
  
  if (filters.addedMonths && filters.addedMonths > 0) {
    filtered = filterAddedMonths(filtered, filters.addedMonths)
  }
  
  if (filters.torrentsFilter === 'with') {
    filtered = filterWithTorrents(filtered)
  } else if (filters.torrentsFilter === 'without') {
    filtered = filterWithoutTorrents(filtered)
  }
  
  if (filters.protectedFilter === 'protected') {
    filtered = filterProtected(filtered)
  } else if (filters.protectedFilter === 'unprotected') {
    filtered = filterUnprotected(filtered)
  }
  
  if (filters.rule && filters.rule !== 'all') {
    filtered = filterByRule(filtered, filters.rule)
  }
  
  return filtered
}

