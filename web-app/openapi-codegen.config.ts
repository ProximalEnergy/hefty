import { defineConfig } from '@openapi-codegen/cli'
import {
  generateReactQueryComponents,
  generateSchemaTypes,
} from '@openapi-codegen/typescript'

export default defineConfig({
  namespace: {
    from: {
      relativePath: '../api/openapi.json',
      source: 'file',
    },
    outputDir: './src/api/_example/openapi-codegen',
    to: async (context) => {
      const filenamePrefix = 'namespace'
      const { schemasFiles } = await generateSchemaTypes(context, {
        filenamePrefix,
      })
      await generateReactQueryComponents(context, {
        filenamePrefix,
        schemasFiles,
        // Add this line to point to your custom hook
        fetcher: '@/api/_example/openapi-codegen/fetcher#useNamespaceFetcher',
      })
    },
  },
})
