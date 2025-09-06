// src/App.jsx
import { Outlet } from 'react-router-dom';
import Sidebar from './components/Sidebar';

function App() {
  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Outlet is a placeholder where React Router will render the current page */}
        <Outlet />
      </main>
    </div>
  );
}

export default App;