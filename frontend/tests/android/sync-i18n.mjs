import { copyFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const source = resolve(testDir, '../../src/i18n/phrases.json')
const target = resolve(testDir, '../../../android/app/src/main/assets/www/i18n-phrases.json')

copyFileSync(source, target)
