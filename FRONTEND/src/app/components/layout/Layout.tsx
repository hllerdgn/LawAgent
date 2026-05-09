import { Outlet } from 'react-router';
import { Navbar } from '../Navbar';
import { Footer } from '../Footer';
import { ChatbotWidget } from '../ChatbotWidget';

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      
      <main className="flex-1">
        <Outlet />
      </main>

      <Footer />
      
      <ChatbotWidget />
    </div>
  );
}
