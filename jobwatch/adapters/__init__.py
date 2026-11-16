from jobwatch.adapters import greenhouse, smartrecruiters, workday

ADAPTERS = {
    "greenhouse": greenhouse.fetch,
    "workday": workday.fetch,
    "smartrecruiters": smartrecruiters.fetch,
}
