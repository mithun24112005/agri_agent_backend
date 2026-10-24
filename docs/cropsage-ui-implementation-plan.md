# CropSage UI implementation plan

## Architecture and installed dependencies

- Vite + React 19 + TypeScript, with Tailwind CSS 4.
- `@assistant-ui/react@0.15.17`, backed by `@assistant-ui/core@0.3.16`.
- The app uses `useRemoteThreadListRuntime`, `useLocalRuntime`, a custom gateway model adapter, a read-only history adapter, and assistant-ui attachment primitives.
- The backend contract remains the existing FastAPI session, history, chat, and image-upload flow.

## Assistant-ui findings and reuse strategy

- Thread, viewport, empty state, suggestions, messages, content parts, attachments, composer, send/cancel controls, scroll-to-bottom, and action bars are already available as assistant-ui primitives and remain the source of truth.
- `MessagePrimitive.Content` merges custom text/image renderers with assistant-ui's native reasoning, tool-call, data, file, source, and generative UI renderers. This preserves native run/activity rendering whenever the runtime supplies those parts.
- Failed assistant turns are rendered with `MessagePrimitive.Error` and `ErrorPrimitive.Root/Message`, with `ActionBarPrimitive.Reload` for recovery. No generic error card is used.
- The old standalone `AgentActivity` status card is removed because it was not tied to a message/run part and could show synthetic activity after the real request had already finished.

## Current UI problems

- Activity was represented by a separate custom store/card instead of assistant-ui message/run state.
- Assistant errors were thrown by the adapter but had no native inline error presentation or retry affordance.
- Styling was strongly botanical and rounded across most surfaces, reducing the native assistant-ui feel.

## Design system and responsive strategy

- Use a neutral monochrome paper/surface system with semantic light/dark variables, visible focus rings, and compact controls. Red is reserved for errors and green is not used as the brand or interaction color.
- Keep the sidebar, compact header, centered conversation column, and bottom composer layout. On small screens the sidebar remains a drawer with a scrim.
- Keep message content readable with a constrained line length, restrained user bubble, native content parts, and action bars that appear on hover or focus.
- Respect reduced motion for entry and spinner animations.

## Verification and acceptance tests

- TypeScript check and Vite production build pass.
- No application code imports a package API that is absent from `@assistant-ui/react@0.15.17`.
- Sending, cancellation, attachment validation/removal, history loading, copy, retry, and theme persistence keep their existing contracts.
- A failed assistant turn exposes `ErrorPrimitive.Message` and a functional native reload action.
- Tool-call/reasoning parts are not replaced by a static status card; assistant-ui remains responsible for rendering them when supplied by the runtime.
