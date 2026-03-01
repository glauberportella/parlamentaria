import { Hero } from "@/components/Hero";
import { EleitorSection } from "@/components/EleitorSection";
import { ParlamentarSection } from "@/components/ParlamentarSection";
import { DemoSection } from "@/components/DemoSection";
import { NumbersSection } from "@/components/NumbersSection";
import { ContribuirSection } from "@/components/ContribuirSection";
import { CTAFinal } from "@/components/CTAFinal";

export default function Home() {
  return (
    <>
      <Hero />
      <EleitorSection />
      <DemoSection />
      <ParlamentarSection />
      <NumbersSection />
      <ContribuirSection />
      <CTAFinal />
    </>
  );
}
