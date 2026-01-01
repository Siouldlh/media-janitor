import React from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

function MainLayout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto md:ml-0">
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default MainLayout

