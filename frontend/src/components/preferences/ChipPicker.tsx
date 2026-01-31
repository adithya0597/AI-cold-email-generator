/**
 * ChipPicker -- multi-select chip/toggle component.
 *
 * Renders a grid of clickable chips. Selected chips are highlighted.
 * Used for job categories, seniority levels, and benefits selection.
 */

interface ChipPickerProps {
  options: readonly string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  columns?: number;
}

export default function ChipPicker({
  options,
  selected,
  onChange,
  columns = 3,
}: ChipPickerProps) {
  const toggle = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  return (
    <div
      className={`grid gap-2`}
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
    >
      {options.map((option) => {
        const isSelected = selected.includes(option);
        return (
          <button
            key={option}
            type="button"
            onClick={() => toggle(option)}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
              isSelected
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
            }`}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}
