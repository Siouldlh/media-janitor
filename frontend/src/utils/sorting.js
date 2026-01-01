/**
 * Fonctions de tri pour les items de plan
 */

export function sortAlphabetical(items, ascending = true) {
  const sorted = [...items].sort((a, b) => {
    const titleA = (a.title || '').toLowerCase()
    const titleB = (b.title || '').toLowerCase()
    if (titleA < titleB) return ascending ? -1 : 1
    if (titleA > titleB) return ascending ? 1 : -1
    return 0
  })
  return sorted
}

export function sortByViewCount(items, ascending = true) {
  const sorted = [...items].sort((a, b) => {
    const countA = a.view_count || 0
    const countB = b.view_count || 0
    return ascending ? countA - countB : countB - countA
  })
  return sorted
}

export function sortByLastViewed(items, ascending = true) {
  const sorted = [...items].sort((a, b) => {
    const dateA = a.last_viewed_at ? new Date(a.last_viewed_at).getTime() : 0
    const dateB = b.last_viewed_at ? new Date(b.last_viewed_at).getTime() : 0
    return ascending ? dateA - dateB : dateB - dateA
  })
  return sorted
}

export function sortByAddedDate(items, ascending = true) {
  const sorted = [...items].sort((a, b) => {
    // Utiliser meta.radarr_added ou meta.sonarr_added si disponible
    const dateA = a.meta?.radarr_added || a.meta?.sonarr_added || a.meta?.added_at
    const dateB = b.meta?.radarr_added || b.meta?.sonarr_added || b.meta?.added_at
    
    const timeA = dateA ? new Date(dateA).getTime() : 0
    const timeB = dateB ? new Date(dateB).getTime() : 0
    return ascending ? timeA - timeB : timeB - timeA
  })
  return sorted
}

export function sortBySize(items, ascending = true) {
  const sorted = [...items].sort((a, b) => {
    const sizeA = a.size_bytes || 0
    const sizeB = b.size_bytes || 0
    return ascending ? sizeA - sizeB : sizeB - sizeA
  })
  return sorted
}

export function applySort(items, sortOption, sortDirection = 'asc') {
  const ascending = sortDirection === 'asc'
  
  switch (sortOption) {
    case 'alphabetical':
      return sortAlphabetical(items, ascending)
    case 'view_count':
      return sortByViewCount(items, ascending)
    case 'last_viewed':
      return sortByLastViewed(items, ascending)
    case 'added_date':
      return sortByAddedDate(items, ascending)
    case 'size':
      return sortBySize(items, ascending)
    default:
      return items
  }
}

