<!-- 
  Список классов для PDF CSS
  Этот файл используется только для того, чтобы Tailwind включил нужные классы в PDF CSS
  Сам файл не рендерится нигде
-->
<template>
  <div>
    <!-- Print utilities -->
    <div class="print:hidden"></div>
    <div class="print:block"></div>
    <div class="print:inline"></div>
    <div class="print:flex"></div>
    <div class="print:text-black"></div>
    <div class="print:bg-white"></div>
    <div class="print:shadow-none"></div>
    <div class="print:border-none"></div>
    
    <!-- PDF Font utilities - используем стандартные Tailwind классы -->
    <div class="print:font-sans"></div>
    <div class="print:font-serif"></div>
    <div class="print:font-mono"></div>
    <div class="font-sans"></div>
    <div class="font-serif"></div>
    <div class="font-mono"></div>
    
    <!-- Typography for PDF -->
    <div class="print:text-sm"></div>
    <div class="print:text-base"></div>
    <div class="print:text-lg"></div>
    <div class="print:text-xl"></div>
    <div class="print:leading-normal"></div>
    <div class="print:leading-relaxed"></div>
    
    <!-- Screen utilities -->
    <div class="screen:block"></div>
    <div class="screen:hidden"></div>
  </div>
</template>
