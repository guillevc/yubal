import { SubscriptionsPanel } from "@/features/subscriptions/subscriptions-panel";
import { useSubscriptions } from "@/features/subscriptions/use-subscriptions";

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
      <h1 className="text-foreground mb-5 text-2xl font-bold">My playlists</h1>

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
    </>
  );
}
