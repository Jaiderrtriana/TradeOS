import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Select } from "../../../components/Select";
import { getPreferences, updatePreferences } from "../api";

const THEME_OPTIONS = [
  { value: "dark", label: "Dark" },
  { value: "light", label: "Light" },
];

const LANGUAGE_OPTIONS = [
  { value: "es", label: "Español" },
  { value: "en", label: "English" },
];

/**
 * TRADEOS_FRONTEND_BLUEPRINT.md §5.7: "Theme selector is grounded in a
 * real field... not decorative." Only theme + language are exposed —
 * notification_settings has no defined shape yet (approved scope
 * decision, CHANGELOG.md Sprint 1.2) and is left untouched.
 */
export function PreferencesPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["preferences"],
    queryFn: getPreferences,
  });

  const { mutate } = useMutation({
    mutationFn: updatePreferences,
    onSuccess: (updated) => {
      queryClient.setQueryData(["preferences"], updated);
    },
  });

  if (isLoading || !data) {
    return <div className="p-6 text-sm text-text-secondary">Loading…</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-text-primary">Preferences</h1>

      <div className="mt-6 flex max-w-md flex-col gap-4">
        <div>
          <p className="mb-1 text-sm text-text-secondary">Theme</p>
          <Select
            value={data.theme}
            onValueChange={(theme) => mutate({ theme })}
            options={THEME_OPTIONS}
            aria-label="Theme"
          />
        </div>

        <div>
          <p className="mb-1 text-sm text-text-secondary">Language</p>
          <Select
            value={data.language}
            onValueChange={(language) => mutate({ language })}
            options={LANGUAGE_OPTIONS}
            aria-label="Language"
          />
        </div>
      </div>
    </div>
  );
}
