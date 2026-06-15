import { useEffect, useMemo, useState } from 'react';
import { Home } from 'lucide-react';
import { ComfyExecutionProvider } from './contexts/ComfyExecutionContext';
import { HomeView } from './components/layout/HomeView';
import { ImageSectionPage } from './pages/ImageSectionPage';
import { VideoSectionPage } from './pages/VideoSectionPage';
import { WorkflowPlaceholderPage } from './pages/WorkflowPlaceholderPage';
import { BreadcrumbTrail, type BreadcrumbItem } from './components/shell/BreadcrumbTrail';
import { SystemStrip } from './components/shell/SystemStrip';
import { ToastProvider } from './components/ui/Toast';
import {
  ACTIVE_TAB_STORAGE_KEY,
  APP_VERSION_LABEL,
  DEFAULT_TAB,
  PAGE_META,
  moduleForTab,
  sectionPageForTab,
  VALID_TABS,
} from './modules/registry';
import { Button } from './ui/primitives';

type ViewMode = 'home' | 'section' | 'workspace';

type AppLocation = {
  view: ViewMode;
  activeTab: string;
};

function resolveTab(tab: string | null | undefined): string {
  if (!tab) return DEFAULT_TAB;
  if (tab === 'home') return DEFAULT_TAB;
  return VALID_TABS.has(tab) ? tab : DEFAULT_TAB;
}

function readActiveTab(): string {
  try {
    return resolveTab(localStorage.getItem(ACTIVE_TAB_STORAGE_KEY));
  } catch {
    return DEFAULT_TAB;
  }
}

function encodeLocation(location: AppLocation): string {
  if (location.view === 'home') return '#/home';
  if (location.activeTab === 'image') return '#/image';
  if (location.activeTab === 'video') return '#/video';
  return `#/tab/${encodeURIComponent(resolveTab(location.activeTab))}`;
}

function readLocationFromHash(): AppLocation {
  const fallbackTab = readActiveTab();
  if (typeof window === 'undefined') return { view: 'home', activeTab: fallbackTab };

  const hash = window.location.hash.replace(/^#\/?/, '').trim();
  if (!hash || hash === 'home') return { view: 'home', activeTab: fallbackTab };
  if (hash === 'image') return { view: 'section', activeTab: 'image' };
  if (hash === 'video') return { view: 'section', activeTab: 'video' };

  if (hash.startsWith('tab/')) {
    const tab = resolveTab(decodeURIComponent(hash.slice(4)));
    if (tab === 'image' || tab === 'video') return { view: 'section', activeTab: tab };
    return { view: 'workspace', activeTab: tab };
  }

  if (VALID_TABS.has(hash)) {
    if (hash === 'image' || hash === 'video') return { view: 'section', activeTab: hash };
    return { view: 'workspace', activeTab: hash };
  }

  return { view: 'home', activeTab: fallbackTab };
}

function parentSectionForTab(tab: string): 'image' | 'video' | null {
  const module = moduleForTab(tab);
  if (module?.area === 'image') return 'image';
  if (module?.area === 'video') return 'video';
  return null;
}

function FeddaApp() {
  const initial = readLocationFromHash();
  const [view, setView] = useState<ViewMode>(initial.view);
  const [activeTab, setActiveTab] = useState(initial.activeTab);

  const navigate = (next: AppLocation) => {
    setView(next.view);
    setActiveTab(next.activeTab);
    window.history.pushState({ fedda: true }, '', encodeLocation(next));
  };

  useEffect(() => {
    try {
      if (activeTab !== 'home') localStorage.setItem(ACTIVE_TAB_STORAGE_KEY, activeTab);
    } catch {}
  }, [activeTab]);

  useEffect(() => {
    const sync = () => {
      const next = readLocationFromHash();
      setView(next.view);
      setActiveTab(next.activeTab);
    };
    if (!window.location.hash) {
      window.history.replaceState({ fedda: true }, '', encodeLocation({ view, activeTab }));
    }
    window.addEventListener('popstate', sync);
    window.addEventListener('hashchange', sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener('hashchange', sync);
    };
  }, [activeTab, view]);

  const breadcrumbs = useMemo((): BreadcrumbItem[] => {
    const items: BreadcrumbItem[] = [
      { label: 'Home', onClick: () => navigate({ view: 'home', activeTab: readActiveTab() }) },
    ];

    if (view === 'section' || view === 'workspace') {
      if (activeTab === 'image' || parentSectionForTab(activeTab) === 'image') {
        items.push({
          label: 'Image Studio',
          onClick: () => navigate({ view: 'section', activeTab: 'image' }),
        });
      } else if (activeTab === 'video' || parentSectionForTab(activeTab) === 'video') {
        items.push({
          label: 'Video Studio',
          onClick: () => navigate({ view: 'section', activeTab: 'video' }),
        });
      }
    }

    if (view === 'workspace') {
      const meta = PAGE_META[activeTab];
      if (meta) items.push({ label: meta.title });
    }

    return items;
  }, [activeTab, view]);

  const openTab = (tab: string) => {
    if (tab === 'image' || tab === 'video') {
      navigate({ view: 'section', activeTab: tab });
      return;
    }
    navigate({ view: 'workspace', activeTab: tab });
  };

  const renderWorkspace = () => {
    const Page = sectionPageForTab(activeTab) ?? WorkflowPlaceholderPage;
    return <Page activeTab={activeTab} onOpenTab={openTab} />;
  };

  return (
    <div className="fedda-app">
      <header className="fedda-header">
        <div className="fedda-header-main">
          <div className="fedda-brand">
            <span className="fedda-brand-mark" />
            <div>
              <strong>{APP_VERSION_LABEL}</strong>
              <BreadcrumbTrail items={breadcrumbs} />
            </div>
          </div>
          <div className="fedda-header-actions">
            {view !== 'home' && (
              <Button variant="ghost" onClick={() => navigate({ view: 'home', activeTab: readActiveTab() })}>
                <Home size={15} />
                Home
              </Button>
            )}
          </div>
        </div>
        <SystemStrip />
      </header>

      <main className="fedda-main">
        {view === 'home' && <HomeView onOpenTab={openTab} />}
        {view === 'section' && activeTab === 'image' && <ImageSectionPage onOpenTab={openTab} />}
        {view === 'section' && activeTab === 'video' && <VideoSectionPage onOpenTab={openTab} />}
        {view === 'workspace' && renderWorkspace()}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <ComfyExecutionProvider>
        <FeddaApp />
      </ComfyExecutionProvider>
    </ToastProvider>
  );
}