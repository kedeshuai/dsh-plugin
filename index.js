// dsh-plugin-whitebox-testing —— skill-only bundle 入口。
// 本包不带运行时行为；apply() 为空操作，仅满足 bundle 激活要求。
// 技能本体在 skills/whitebox-testing/SKILL.md，脚本在 skills/whitebox-testing/scripts/。
export const name = 'whitebox-testing'

export function apply() {}

export default { name, apply }
