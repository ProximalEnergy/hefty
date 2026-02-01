import type * as types from '@/api/schema'

type MethodFor<TPath extends keyof types.paths> = NonNullable<
  types.paths[TPath]
>

type PathParams<
  TPath extends keyof types.paths,
  TMethod extends keyof MethodFor<TPath>,
> = MethodFor<TPath>[TMethod] extends { parameters: { path: infer Params } }
  ? Params
  : never

type QueryParams<
  TPath extends keyof types.paths,
  TMethod extends keyof MethodFor<TPath>,
> = MethodFor<TPath>[TMethod] extends { parameters: { query?: infer Params } }
  ? Params
  : never

type JsonResponse<
  TPath extends keyof types.paths,
  TMethod extends keyof MethodFor<TPath>,
> = Response<TPath, TMethod>

type Response<
  TPath extends keyof types.paths,
  TMethod extends keyof MethodFor<TPath>,
  TStatus extends number = 200,
  TContentType extends string = 'application/json',
> = MethodFor<TPath>[TMethod] extends {
  responses: {
    [K in TStatus]: { content: { [C in TContentType]: infer Body } }
  }
}
  ? Body
  : never

export type Endpoint<
  TPath extends keyof types.paths,
  TMethod extends keyof MethodFor<TPath>,
> = {
  PathParams: PathParams<TPath, TMethod>
  QueryParams: QueryParams<TPath, TMethod>
  Response: JsonResponse<TPath, TMethod>
}
