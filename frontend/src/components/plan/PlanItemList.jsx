import React, { useState, useMemo } from 'react'
import PlanItemCard from './PlanItemCard'
import { applySort } from '../../utils/sorting'
import { applyFilters } from '../../utils/filtering'

function PlanItemList({ items, onToggle, onProtect, filters, sortOption, sortDirection }) {
  const [showFilters, setShowFilters] = useState(false)

  const filteredAndSorted = useMemo(() => {
    let result = items || []
    
    // Apply filters
    if (filters) {
      result = applyFilters(result, filters)
    }
    
    // Apply sorting
    if (sortOption && sortDirection) {
      result = applySort(result, sortOption, sortDirection)
    }
    
    return result
  }, [items, filters, sortOption, sortDirection])

  if (!items || items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-12 text-center">
        <p className="text-gray-500">Aucun item dans ce plan</p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-600">
          {filteredAndSorted.length} item{filteredAndSorted.length > 1 ? 's' : ''} affiché{filteredAndSorted.length > 1 ? 's' : ''}
          {filteredAndSorted.length !== items.length && ` (${items.length} au total)`}
        </p>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          {showFilters ? 'Masquer filtres' : 'Afficher filtres'}
        </button>
      </div>

      <div className="space-y-4">
        {filteredAndSorted.map((item) => (
          <PlanItemCard
            key={item.id}
            item={item}
            onToggle={onToggle}
            onProtect={onProtect}
          />
        ))}
      </div>
    </div>
  )
}

export default PlanItemList

