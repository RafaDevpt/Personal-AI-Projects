/* eslint-disable */

// @ts-nocheck

// Gerado originalmente pelo TanStack Router no Lovable; sem o bloco do TanStack Start (SSR),
// que não é usado na versão estática.

import { Route as rootRouteImport } from './routes/__root'
import { Route as IndexRouteImport } from './routes/index'
import { Route as IrsRouteImport } from './routes/irs'
import { Route as RegrasRouteImport } from './routes/regras'
import { Route as SalarioRouteImport } from './routes/salario'

const IndexRoute = IndexRouteImport.update({
  id: '/',
  path: '/',
  getParentRoute: () => rootRouteImport,
} as any)
const IrsRoute = IrsRouteImport.update({
  id: '/irs',
  path: '/irs',
  getParentRoute: () => rootRouteImport,
} as any)
const RegrasRoute = RegrasRouteImport.update({
  id: '/regras',
  path: '/regras',
  getParentRoute: () => rootRouteImport,
} as any)
const SalarioRoute = SalarioRouteImport.update({
  id: '/salario',
  path: '/salario',
  getParentRoute: () => rootRouteImport,
} as any)

export interface FileRoutesByFullPath {
  '/': typeof IndexRoute
  '/irs': typeof IrsRoute
  '/regras': typeof RegrasRoute
  '/salario': typeof SalarioRoute
}
export interface FileRoutesByTo {
  '/': typeof IndexRoute
  '/irs': typeof IrsRoute
  '/regras': typeof RegrasRoute
  '/salario': typeof SalarioRoute
}
export interface FileRoutesById {
  __root__: typeof rootRouteImport
  '/': typeof IndexRoute
  '/irs': typeof IrsRoute
  '/regras': typeof RegrasRoute
  '/salario': typeof SalarioRoute
}
export interface FileRouteTypes {
  fileRoutesByFullPath: FileRoutesByFullPath
  fullPaths: '/' | '/irs' | '/regras' | '/salario'
  fileRoutesByTo: FileRoutesByTo
  to: '/' | '/irs' | '/regras' | '/salario'
  id: '__root__' | '/' | '/irs' | '/regras' | '/salario'
  fileRoutesById: FileRoutesById
}
export interface RootRouteChildren {
  IndexRoute: typeof IndexRoute
  IrsRoute: typeof IrsRoute
  RegrasRoute: typeof RegrasRoute
  SalarioRoute: typeof SalarioRoute
}

declare module '@tanstack/react-router' {
  interface FileRoutesByPath {
    '/': {
      id: '/'
      path: '/'
      fullPath: '/'
      preLoaderRoute: typeof IndexRouteImport
      parentRoute: typeof rootRouteImport
    }
    '/irs': {
      id: '/irs'
      path: '/irs'
      fullPath: '/irs'
      preLoaderRoute: typeof IrsRouteImport
      parentRoute: typeof rootRouteImport
    }
    '/regras': {
      id: '/regras'
      path: '/regras'
      fullPath: '/regras'
      preLoaderRoute: typeof RegrasRouteImport
      parentRoute: typeof rootRouteImport
    }
    '/salario': {
      id: '/salario'
      path: '/salario'
      fullPath: '/salario'
      preLoaderRoute: typeof SalarioRouteImport
      parentRoute: typeof rootRouteImport
    }
  }
}

const rootRouteChildren: RootRouteChildren = {
  IndexRoute: IndexRoute,
  IrsRoute: IrsRoute,
  RegrasRoute: RegrasRoute,
  SalarioRoute: SalarioRoute,
}
export const routeTree = rootRouteImport
  ._addFileChildren(rootRouteChildren)
  ._addFileTypes<FileRouteTypes>()
