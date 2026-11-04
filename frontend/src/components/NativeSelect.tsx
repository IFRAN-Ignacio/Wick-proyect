import type { SelectHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

/** Select nativo con el estilo de los inputs de shadcn (rápido y accesible por teclado). */
export function NativeSelect({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        'h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      {...props}
    />
  )
}
