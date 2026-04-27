export const isPathActive = (pathname: string, path: string) => {
  if (!pathname.startsWith(path)) {
    return false
  }

  return pathname[path.length] === undefined
}
