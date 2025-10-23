// frontend/scripts/generate-enums.mjs
import fs from 'fs'
import path from 'path'

// Get input/output file paths from command line arguments
const [inputFile, outputFile] = process.argv.slice(2)

if (!inputFile || !outputFile) {
  console.error(
    'Usage: node generate-enums.mjs <path-to-openapi.json> <path-to-output.ts>',
  )
  process.exit(1)
}

// --- Script Logic ---
try {
  // 1. Read and parse the openapi.json file
  const openapiSpec = JSON.parse(fs.readFileSync(inputFile, 'utf-8'))
  const schemas = openapiSpec.components.schemas

  let content = `// THIS FILE IS AUTO-GENERATED. DO NOT EDIT.\n// Run "npm run generate-api" to regenerate.\n\n`
  let enumsFound = 0

  // 2. Iterate over all schemas to find enums
  for (const schemaName in schemas) {
    const schema = schemas[schemaName]

    // An enum has both `enum` and the FastAPI-specific `x-enum-varnames` properties
    if (schema.enum && schema['x-enum-varnames']) {
      enumsFound++
      const names = schema['x-enum-varnames']
      const values = schema.enum

      // 3. Build the 'as const' object string
      content += `export const ${schemaName} = {\n`
      for (let i = 0; i < names.length; i++) {
        const value =
          typeof values[i] === 'string' ? `'${values[i]}'` : values[i]
        content += `  ${names[i]}: ${value},\n`
      }
      content += `} as const;\n\n`
    }
  }

  // 4. Write the final content to the output file
  const outputDir = path.dirname(outputFile)
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }
  fs.writeFileSync(outputFile, content)

  console.log(
    `✅ Successfully generated ${enumsFound} enum objects in ${outputFile}`,
  )
} catch (error) {
  console.error('❌ Error generating enum file:', error)
  process.exit(1)
}
