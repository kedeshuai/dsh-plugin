/**
 * @file  test_framework.h
 * @brief 极简单元测试框架: CHECK 断言 + 用例运行 + 汇总。
 *        用法:
 *          TEST(name) { CHECK(cond, "msg"); CHECK_EQ(a, b); }
 *          int main(void) { RUN_TEST(name); return TEST_SUMMARY(); }
 */
#ifndef __TEST_FRAMEWORK_H__
#define __TEST_FRAMEWORK_H__

#include <stdio.h>
#include <string.h>

static int g_tf_pass = 0;
static int g_tf_fail = 0;
static int g_tf_case_fail = 0;

#define TF_FAILF(...) do { \
    printf("    [FAIL] %s:%d  ", __FILE__, __LINE__); \
    printf(__VA_ARGS__); \
    printf("\n"); \
    g_tf_case_fail++; \
} while (0)

#define CHECK(cond, ...) do { \
    if (cond) { g_tf_pass++; } \
    else { g_tf_fail++; TF_FAILF(__VA_ARGS__); } \
} while (0)

#define CHECK_EQ(actual, expected) do { \
    long long _a = (long long)(actual); \
    long long _e = (long long)(expected); \
    if (_a == _e) { g_tf_pass++; } \
    else { g_tf_fail++; TF_FAILF("%s == %s: got %lld, want %lld", #actual, #expected, _a, _e); } \
} while (0)

#define CHECK_NE(actual, expected) do { \
    long long _a = (long long)(actual); \
    long long _e = (long long)(expected); \
    if (_a != _e) { g_tf_pass++; } \
    else { g_tf_fail++; TF_FAILF("%s != %s: both %lld", #actual, #expected, _a); } \
} while (0)

#define TEST(name) static void name(void)

#define RUN_TEST(name) do { \
    int _before = g_tf_fail; \
    printf("[RUN ] %s\n", #name); \
    name(); \
    if (g_tf_fail == _before) printf("[ OK ] %s\n", #name); \
    else printf("[FAIL] %s\n", #name); \
} while (0)

static int TEST_SUMMARY(void) \
{ \
    printf("\n==== SUMMARY: %d checks passed, %d failed ====\n", g_tf_pass, g_tf_fail); \
    return (g_tf_fail == 0) ? 0 : 1; \
}

#endif /* __TEST_FRAMEWORK_H__ */
