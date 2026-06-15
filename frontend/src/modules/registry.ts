import { Bot, Images, LayoutDashboard, Sparkles, Video, type LucideIcon } from 'lucide-react';
import type { ComponentType } from 'react';
import type { WorkspacePageProps } from '../types/pages';
import { GalleryPage } from '../pages/GalleryPage';
import { LibraryPage } from '../pages/LibraryPage';
import { OllamaPage } from '../pages/OllamaPage';
import { WorkflowPlaceholderPage } from '../pages/WorkflowPlaceholderPage';

export type ModulePack = 'core' | 'booster';
export type ModuleArea = 'home' | 'image' | 'video' | 'system';
export type ModuleStatus = 'verified' | 'lab' | 'parked' | 'planned';
export type SourceModuleId = 'core-shell' | string;

export interface FeddaCardMedia {
  poster: string;
  video?: string;
}

export interface FeddaModule {
  id: string;
  sourceModuleId: SourceModuleId;
  label: string;
  description: string;
  area: ModuleArea;
  pack: ModulePack;
  enabled: boolean;
  tabs: string[];
  workflows?: string[];
  defaultTab: string;
  status?: ModuleStatus;
  statusLabel?: string;
  Icon: LucideIcon;
  card?: FeddaCardMedia;
  /** Lazy page component for workspace tabs. Section/home views use layout components. */
  Page?: ComponentType<WorkspacePageProps>;
}

export const APP_VERSION_LABEL = 'FEDDA Hub v20';
export const ACTIVE_TAB_STORAGE_KEY = 'fedda_v20_active_tab';
export const UI_LOG_STORAGE_KEY = 'fedda_v20_ui_logs';

const placeholderCard = (slug: string): FeddaCardMedia => ({
  poster: `/cards/placeholders/${slug}.svg`,
});

export const FEDDA_MODULES: FeddaModule[] = [
  {
    id: 'image-studio',
    sourceModuleId: 'core-shell',
    label: 'Image Studio',
    description: 'Text, reference, and LoRA-driven image workflows.',
    area: 'home',
    pack: 'core',
    enabled: true,
    tabs: ['image'],
    defaultTab: 'image',
    Icon: Sparkles,
    card: placeholderCard('image-studio'),
  },
  {
    id: 'video-studio',
    sourceModuleId: 'core-shell',
    label: 'Video Studio',
    description: 'Motion and video workflows with a consistent workbench.',
    area: 'home',
    pack: 'core',
    enabled: true,
    tabs: ['video'],
    defaultTab: 'video',
    Icon: Video,
    card: placeholderCard('video-studio'),
  },
  {
    id: 'gallery',
    sourceModuleId: 'core-shell',
    label: 'Gallery',
    description: 'Generated images and videos in one place.',
    area: 'system',
    pack: 'core',
    enabled: true,
    tabs: ['gallery'],
    defaultTab: 'gallery',
    Icon: Images,
    card: placeholderCard('gallery'),
    Page: GalleryPage,
  },
  {
    id: 'lora-library',
    sourceModuleId: 'core-shell',
    label: 'LoRA Library',
    description: 'Install, import, and manage LoRA packs.',
    area: 'system',
    pack: 'core',
    enabled: true,
    tabs: ['library'],
    defaultTab: 'library',
    Icon: LayoutDashboard,
    card: placeholderCard('library'),
    Page: LibraryPage,
  },
  {
    id: 'ollama-models',
    sourceModuleId: 'core-shell',
    label: 'Ollama Models',
    description: 'Local text and vision models for FEDDA tools.',
    area: 'system',
    pack: 'core',
    enabled: true,
    tabs: ['ollama'],
    defaultTab: 'ollama',
    Icon: Bot,
    card: placeholderCard('ollama'),
    Page: OllamaPage,
  },
];

export const ENABLED_MODULES = FEDDA_MODULES.filter((module) => module.enabled);

export const VALID_TABS = new Set(
  ENABLED_MODULES.flatMap((module) => module.tabs),
);

export const DEFAULT_TAB = 'home';

export const PAGE_META: Record<string, { title: string; subtitle?: string }> = Object.fromEntries(
  ENABLED_MODULES.flatMap((module) =>
    module.tabs.map((tab) => [
      tab,
      { title: module.label, subtitle: module.description },
    ]),
  ),
);

PAGE_META.home = { title: 'Home', subtitle: 'Choose a studio or system tool' };
PAGE_META.image = { title: 'Image Studio', subtitle: 'Pick an image workflow' };
PAGE_META.video = { title: 'Video Studio', subtitle: 'Pick a video workflow' };

export function moduleForTab(tab: string): FeddaModule | undefined {
  return ENABLED_MODULES.find((module) => module.tabs.includes(tab));
}

export function workflowModulesForArea(area: 'image' | 'video'): FeddaModule[] {
  return ENABLED_MODULES.filter(
    (module) => module.area === area && module.workflows && module.workflows.length > 0,
  );
}

export function sectionPageForTab(tab: string): ComponentType<WorkspacePageProps> {
  const module = moduleForTab(tab);
  return module?.Page ?? WorkflowPlaceholderPage;
}