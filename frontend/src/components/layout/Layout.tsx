import Sidebar from './Sidebar'
import Header from './Header'
import MainArea from './MainArea'

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <MainArea />
      </div>
    </div>
  )
}
