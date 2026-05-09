import { createBrowserRouter } from 'react-router';
import { Layout } from './components/layout/Layout';
import { AdminLayout } from './components/layout/AdminLayout';
import { HomePage } from './pages/HomePage';
import { AboutPage } from './pages/AboutPage';
import { PracticeAreasPage } from './pages/PracticeAreasPage';
import { PracticeAreaDetailPage } from './pages/PracticeAreaDetailPage';
import { BlogPage } from './pages/BlogPage';
import { BlogPostPage } from './pages/BlogPostPage';
import { WorkPrinciplesPage } from './pages/WorkPrinciplesPage';
import { ContactPage } from './pages/ContactPage';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { AdminPracticeAreas } from './pages/admin/AdminPracticeAreas';
import { AdminBlog } from './pages/admin/AdminBlog';
import { AdminMessages } from './pages/admin/AdminMessages';
import { AdminSettings } from './pages/admin/AdminSettings';
import { AdminLogin } from './pages/admin/AdminLogin';
import { NotFound } from './pages/NotFound';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      { index: true, Component: HomePage },
      { path: 'about', Component: AboutPage },
      { path: 'practice-areas', Component: PracticeAreasPage },
      { path: 'practice-areas/:slug', Component: PracticeAreaDetailPage },
      { path: 'blog', Component: BlogPage },
      { path: 'blog/:slug', Component: BlogPostPage },
      { path: 'work-principles', Component: WorkPrinciplesPage },
      { path: 'contact', Component: ContactPage },
    ],
  },
  {
    path: '/admin',
    children: [
      { index: true, Component: AdminLogin },
      {
        path: 'dashboard',
        Component: AdminLayout,
        children: [
          { index: true, Component: AdminDashboard },
          { path: 'practice-areas', Component: AdminPracticeAreas },
          { path: 'blog', Component: AdminBlog },
          { path: 'messages', Component: AdminMessages },
          { path: 'settings', Component: AdminSettings },
        ],
      },
    ],
  },
  {
    path: '*',
    Component: NotFound,
  },
]);
