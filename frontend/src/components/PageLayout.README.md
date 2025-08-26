# PageLayout Component

A reusable layout component that provides consistent max-width and padding across all pages in the Evidence Seeker Platform.

## Usage

```typescript
import PageLayout from "../components/PageLayout";

// For wide layouts (lists, dashboards)
<PageLayout variant="wide">
  <YourContent />
</PageLayout>

// For narrow layouts (forms, focused content)
<PageLayout variant="narrow">
  <YourContent />
</PageLayout>

// With custom className
<PageLayout variant="wide" className="custom-class">
  <YourContent />
</PageLayout>
```

## Variants

### `wide` (default)
- **Max Width**: `max-w-7xl` (1280px)
- **Use Case**: Lists, dashboards, multi-column layouts
- **Example**: EvidenceSeekerList, Dashboard

### `narrow`
- **Max Width**: `max-w-2xl` (672px)
- **Use Case**: Forms, focused content, single-column layouts
- **Example**: EvidenceSeekerForm, UploadForm

## Layout Structure

```jsx
<main className="max-w-[variant] mx-auto py-6 sm:px-6 lg:px-8 [custom-class]">
  <div className="px-4 py-6 sm:px-0">
    {/* Your content goes here */}
  </div>
</main>
```

## Migration Guide

### Before (inconsistent)
```jsx
// Different components had different approaches
<div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
  <div className="px-4 py-6 sm:px-0">
    <Content />
  </div>
</div>

// Or just no layout at all
<Content />
```

### After (consistent)
```jsx
<PageLayout variant="wide">
  <Content />
</PageLayout>
```

## Benefits

✅ **Consistency** - All pages use the same layout structure
✅ **Maintainability** - Change layout in one place
✅ **Developer Experience** - Simple import instead of remembering class strings
✅ **Responsive** - Proper responsive padding and margins
✅ **Type Safety** - TypeScript variants prevent typos
✅ **Future-proof** - Easy to add new variants (compact, spacious, etc.)

## Best Practices

1. **Choose the right variant**:
   - Use `wide` for lists and multi-column content
   - Use `narrow` for forms and focused content

2. **Don't nest PageLayout**:
   - Use PageLayout at the top level of your component
   - Don't wrap PageLayout with another PageLayout

3. **Custom styling**:
   - Use the `className` prop for component-specific styling
   - Avoid overriding the core layout styles

## Examples

### List Component
```typescript
const MyListComponent = () => (
  <PageLayout variant="wide">
    <div className="space-y-4">
      <h2>My Items</h2>
      <ItemList />
    </div>
  </PageLayout>
);
```

### Form Component
```typescript
const MyFormComponent = () => (
  <PageLayout variant="narrow">
    <div className="bg-white shadow-sm rounded-lg border border-gray-200">
      <FormHeader />
      <FormContent />
    </div>
  </PageLayout>
);
```

## Responsive Design

The layout automatically provides:
- **Mobile**: Smaller padding, full-width within container
- **Tablet**: Medium padding
- **Desktop**: Larger padding with max-width constraint

This ensures consistent spacing across all screen sizes.
