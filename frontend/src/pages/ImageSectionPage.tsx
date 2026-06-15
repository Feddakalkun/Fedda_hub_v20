import { SectionView } from '../components/layout/SectionView';

interface ImageSectionPageProps {
  onOpenTab: (tab: string) => void;
}

export function ImageSectionPage({ onOpenTab }: ImageSectionPageProps) {
  return <SectionView area="image" onOpenTab={onOpenTab} />;
}