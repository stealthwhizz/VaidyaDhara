// src/App.jsx
import { Outlet } from 'react-router-dom';
import Sidebar from './components/Sidebar';

function App() {
  return (
    <div className="flex h-screen bg-gray-900 text-white font-sans">
      <Sidebar />
      <main className="flex-1 flex flex-col">
        {/* Outlet is a placeholder where React Router will render the current page */}
        <Outlet />
      </main>
    </div>
  );
}

export default App;