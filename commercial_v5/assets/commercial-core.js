/* Facil Pedido V5 - calculo comercial de exibicao com valores em centavos.
 * NAO substitui cotacao nem validacao autoritativa do servidor ERP. */
(() => {
  "use strict";
  function scaled(value) {
    let n = Number(value ?? 0);
    if (!Number.isFinite(n) || Math.abs(n) > 1e12) throw new Error("Valor monetario invalido.");
    return BigInt(Math.round((n + Math.sign(n) * Number.EPSILON) * 100));
  }
  const real = (c) => Number(c) / 100;
  function validNonnegative(value, field) {
    const n = Number(value ?? 0);
    if (!Number.isFinite(n) || n < 0) throw new Error(`${field} invalido.`);
    return n;
  }
  function discount(spec, gross, field) {
    const type = spec?.type || "percent";
    const value = validNonnegative(spec?.value || 0, field);
    if (type !== "percent" && type !== "amount") throw new Error(`Unidade de ${field} invalida.`);
    if (type === "percent") {
      if (value > 100) throw new Error(`${field} ultrapassa 100%.`);
      return BigInt(Math.round(Number(gross) * value / 100));
    }
    const cents = scaled(value);
    if (cents > gross) throw new Error(`${field} ultrapassa o valor disponivel.`);
    return cents;
  }
  function calculate(input = {}) {
    if (!Array.isArray(input.items) || input.items.length > 100) throw new Error("Itens invalidos.");
    let gross = 0n, itemDiscount = 0n;
    const items = input.items.map(item => {
      const qty = validNonnegative(item.quantity, "Quantidade");
      const price = validNonnegative(item.unit_price, "Preco unitario");
      if (qty <= 0 || qty > 100000) throw new Error("Quantidade fora dos limites.");
      const before = scaled(qty * price);
      const spec = item.discount_spec || {type:"percent", value:item.discount_percent ?? item.discount ?? 0};
      const off = discount(spec, before, "Desconto do item");
      gross += before; itemDiscount += off;
      return {...item, gross:real(before), discount:real(off), total:real(before-off)};
    });
    const subtotal = gross-itemDiscount;
    const general = discount(input.discount_spec || {type:"percent",value:input.discount ?? 0}, subtotal, "Desconto geral");
    const freight = scaled(validNonnegative(input.freight,"Frete"));
    const assembly = scaled(validNonnegative(input.assembly,"Montagem"));
    const total = subtotal-general+freight+assembly;
    const payments = Array.isArray(input.payments) ? input.payments : [];
    let planned = 0n;
    for (const p of payments) planned += scaled(validNonnegative(p.amount,"Pagamento"));
    if (planned > total + 1n) throw new Error("Os pagamentos planejados ultrapassam o total.");
    return {...input, items, gross:real(gross), item_discount:real(itemDiscount), subtotal:real(subtotal), discount:real(general), freight:real(freight), assembly:real(assembly), total:real(total), planned_total:real(planned), remaining:real(total-planned)};
  }
  window.FPCommercialMoney = {scaled, calculate};
})();
