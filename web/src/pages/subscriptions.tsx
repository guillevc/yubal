import { BlurFade } from "../components/magicui/blur-fade";
import { SubscriptionsPanel } from "../components/subscriptions/subscriptions-panel";
import { useSubscriptions } from "../hooks/use-subscriptions";

export function SubscriptionsPage() {
  const {
    subscriptions,
    addSubscription,
    updateSubscription,
    deleteSubscription,
    syncSubscription,
    syncAll,
  } = useSubscriptions();

  const handleToggleEnabled = async (id: string, enabled: boolean) => {
    await updateSubscription(id, { enabled });
  };

  return (
    <>
      {/* Page Title */}
      <BlurFade delay={0.025} direction="up">
        <h1 className="text-foreground mb-6 text-2xl font-bold">
          My playlists
        </h1>
      </BlurFade>

      <BlurFade delay={0.05} direction="up">
        <section className="mb-6">
          <SubscriptionsPanel
            subscriptions={subscriptions}
            onAddSubscription={addSubscription}
            onToggleEnabled={handleToggleEnabled}
            onSync={syncSubscription}
            onSyncAll={syncAll}
            onDelete={deleteSubscription}
          />
        </section>
      </BlurFade>
    </>
  );
}
