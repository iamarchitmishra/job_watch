from jobwatch.adapters import ashby, greenhouse, lever, smartrecruiters, workday

ADAPTERS = {
    "greenhouse": greenhouse.fetch,
    "workday": workday.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
}
