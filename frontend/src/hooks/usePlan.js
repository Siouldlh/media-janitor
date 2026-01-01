import { useState, useEffect, useCallback } from 'react'
import { getPlan, updateItems } from '../api'

const usePlan = (planId) => {
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadPlan = useCallback(async () => {
    if (!planId || planId === 'null' || planId === 'undefined') {
      setPlan(null)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await getPlan(planId)
      setPlan(data)
    } catch (err) {
      setError(err.message)
      setPlan(null)
    } finally {
      setLoading(false)
    }
  }, [planId])

  const updateItemSelection = useCallback(async (itemId, selected) => {
    if (!planId) return

    // Optimistic update
    setPlan(prevPlan => {
      if (!prevPlan) return prevPlan
      return {
        ...prevPlan,
        items: prevPlan.items.map(item =>
          item.id === itemId ? { ...item, selected } : item
        )
      }
    })

    try {
      await updateItems(planId, [{ id: itemId, selected }])
    } catch (err) {
      // Revert on error
      loadPlan()
      throw err
    }
  }, [planId, loadPlan])

  const updateAllItems = useCallback(async (selected) => {
    if (!planId) return

    // Optimistic update
    setPlan(prevPlan => {
      if (!prevPlan) return prevPlan
      return {
        ...prevPlan,
        items: prevPlan.items.map(item => ({ ...item, selected }))
      }
    })

    try {
      await updateItems(planId, [], selected)
    } catch (err) {
      loadPlan()
      throw err
    }
  }, [planId, loadPlan])

  useEffect(() => {
    loadPlan()
  }, [loadPlan])

  const selectedCount = plan?.items?.filter(item => item.selected).length || 0
  const totalCount = plan?.items?.length || 0

  return {
    plan,
    loading,
    error,
    selectedCount,
    totalCount,
    loadPlan,
    updateItemSelection,
    updateAllItems,
  }
}

export default usePlan

