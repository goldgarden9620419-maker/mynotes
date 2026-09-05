import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Filter, MapPin, Users } from "lucide-react";
import { ReactNode } from "react";

export function Features() {
  return (
    <section className="py-16 md:py-28">
      <div className="mx-auto max-w-5xl px-6">
        <div className="text-center">
          <h2 className="text-balance text-3xl font-semibold sm:text-4xl">
            그 맛집, 사실 광고비 순위예요
          </h2>
          <p className="mt-4 text-muted-foreground">
            블로그·플레이스 상위 노출은 돈이면 됩니다. 저희는 광고 없이, 딱
            3가지 기준으로만 골라드려요.
          </p>
        </div>
        <div className="mx-auto mt-10 grid max-w-sm grid-cols-1 gap-6 *:text-center sm:max-w-full sm:grid-cols-3 md:mt-16">
          <Card className="group border-0 bg-secondary shadow-none">
            <CardHeader className="pb-3">
              <CardDecorator>
                <Filter className="size-6" aria-hidden />
              </CardDecorator>
              <h3 className="mt-6 font-medium">프랜차이즈는 제외</h3>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                스타벅스, 맥도날드 같은 대형 프랜차이즈는 자동으로 걸러내고,
                진짜 로컬 맛집만 남겨요.
              </p>
            </CardContent>
          </Card>

          <Card className="group border-0 bg-secondary shadow-none">
            <CardHeader className="pb-3">
              <CardDecorator>
                <MapPin className="size-6" aria-hidden />
              </CardDecorator>
              <h3 className="mt-6 font-medium">실시간 위치 기반</h3>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                GPS로 확인한 현재 위치를 기준으로, 가까운 순서대로 정확하게
                찾아드려요.
              </p>
            </CardContent>
          </Card>

          <Card className="group border-0 bg-secondary shadow-none">
            <CardHeader className="pb-3">
              <CardDecorator>
                <Users className="size-6" aria-hidden />
              </CardDecorator>
              <h3 className="mt-6 font-medium">상황에 맞는 추천</h3>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                인원수와 모임 성격(가족·데이트·회식·혼밥)을 반영해서 딱 맞는
                곳을 골라드려요.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

const CardDecorator = ({ children }: { children: ReactNode }) => (
  <div
    aria-hidden
    className="relative mx-auto size-36 [mask-image:radial-gradient(ellipse_50%_50%_at_50%_50%,#000_70%,transparent_100%)]"
  >
    <div className="absolute inset-0 [--border:black] bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:24px_24px] opacity-10" />
    <div className="bg-background absolute inset-0 m-auto flex size-12 items-center justify-center rounded-full border border-border text-accent">
      {children}
    </div>
  </div>
);
