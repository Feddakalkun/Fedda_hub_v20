import { SectionView } from '../components/layout/SectionView';

interface VideoSectionPageProps {
  onOpenTab: (tab: string) => void;
}

export function VideoSectionPage({ onOpenTab }: VideoSectionPageProps) {
  return <SectionView area="video" onOpenTab={onOpenTab} />;
}