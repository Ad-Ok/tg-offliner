<template>
  <div>
    <h1>Лента постов</h1>
    <router-view />
  </div>
</template>

<script>
export default {};
</script>

<style>
.loading {
  font-size: 18px;
  text-align: center;
  margin-top: 20px;
}

.reactions {
  display: flex;
  margin-top: 10px;
}

.reaction {
  display: flex;
  align-items: center;
  gap: 5px;
}

.message {
  margin-bottom: 20px;
}
</style>
